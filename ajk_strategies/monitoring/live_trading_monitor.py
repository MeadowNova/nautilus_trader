"""
Live Trading Monitor - Records trading session data to PostgreSQL

This module subscribes to NautilusTrader events and writes them to the
PostgreSQL database for monitoring via Prometheus and Grafana.
"""

import os
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from nautilus_trader.common.component import MessageBus
from nautilus_trader.model.events import (
    AccountState,
    OrderFilled,
    OrderAccepted,
    OrderRejected,
    PositionOpened,
    PositionChanged,
    PositionClosed,
)
from nautilus_trader.model.identifiers import TraderId, StrategyId


class LiveTradingMonitor:
    """
    Monitors live trading sessions and records data to PostgreSQL.
    """
    
    def __init__(
        self,
        msgbus: MessageBus,
        trader_id: TraderId,
        strategy_id: StrategyId,
        environment: str = "TESTNET",
    ):
        self.msgbus = msgbus
        self.trader_id = str(trader_id)
        self.strategy_id = str(strategy_id)
        self.environment = environment
        self.session_id: Optional[int] = None
        
        # Database connection
        load_dotenv()
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5435)),
            'database': os.getenv('DB_NAME', 'nautilus_trader'),
            'user': os.getenv('DB_USER', 'nautilus'),
            'password': os.getenv('DB_PASSWORD'),
        }
        
        # Initialize session
        self._init_session()
        
        # Subscribe to events
        self._subscribe_events()
    
    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def _init_session(self):
        """Initialize live trading session in database"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO ai_extensions.live_sessions 
                        (trader_id, strategy_id, exchange_venue, environment, status, started_at, initial_balance)
                        VALUES (%s, %s, 'BYBIT', %s, 'RUNNING', NOW(), 100000.00)
                        RETURNING id;
                    """, (self.trader_id, self.strategy_id, self.environment))
                    
                    self.session_id = cur.fetchone()[0]
                    conn.commit()
                    print(f"✅ Live trading session created: ID={self.session_id}")
        except Exception as e:
            print(f"❌ Failed to create session: {e}")
    
    def _subscribe_events(self):
        """Subscribe to relevant trading events"""
        # Account updates
        self.msgbus.subscribe(
            topic="events.account.*",
            handler=self.on_account_event,
            priority=5
        )
        
        # Order events
        self.msgbus.subscribe(
            topic="events.order.*",
            handler=self.on_order_event,
            priority=5
        )
        
        # Position events
        self.msgbus.subscribe(
            topic="events.position.*",
            handler=self.on_position_event,
            priority=5
        )
        
        print("✅ Subscribed to trading events for monitoring")
    
    def on_account_event(self, event):
        """Handle account state updates"""
        if not isinstance(event, AccountState):
            return
        
        try:
            # Record equity snapshot
            total_equity = sum(b.total.as_double() for b in event.balances if 'USD' in str(b.total.currency))
            cash_balance = sum(b.free.as_double() for b in event.balances if 'USD' in str(b.total.currency))
            
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO ai_extensions.live_equity_snapshots
                        (session_id, snapshot_timestamp, total_equity, cash_balance, num_open_positions)
                        VALUES (%s, NOW(), %s, %s, 0)
                        ON CONFLICT DO NOTHING;
                    """, (self.session_id, total_equity, cash_balance))
                    conn.commit()
        except Exception as e:
            print(f"⚠️ Error recording equity: {e}")
    
    def on_order_event(self, event):
        """Handle order events"""
        if not self.session_id:
            return
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if isinstance(event, OrderAccepted):
                        # Insert or update order
                        cur.execute("""
                            INSERT INTO ai_extensions.live_orders
                            (session_id, order_id, client_order_id, instrument_id, side, order_type, 
                             status, quantity, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, 'ACCEPTED', %s, NOW())
                            ON CONFLICT (order_id) DO UPDATE SET
                                status = 'ACCEPTED',
                                accepted_at = NOW();
                        """, (
                            self.session_id,
                            str(event.order_id),
                            str(event.client_order_id),
                            str(event.instrument_id),
                            str(event.order_side),
                            str(event.order_type),
                            float(event.quantity),
                        ))
                    
                    elif isinstance(event, OrderFilled):
                        # Update order as filled
                        cur.execute("""
                            UPDATE ai_extensions.live_orders
                            SET status = 'FILLED',
                                filled_qty = %s,
                                avg_fill_price = %s,
                                filled_at = NOW()
                            WHERE order_id = %s;
                        """, (
                            float(event.last_qty),
                            float(event.last_px),
                            str(event.order_id),
                        ))
                        
                        # Record execution
                        cur.execute("""
                            INSERT INTO ai_extensions.live_executions
                            (session_id, order_id, execution_id, quantity, price, executed_at)
                            VALUES (%s, %s, %s, %s, %s, NOW());
                        """, (
                            self.session_id,
                            str(event.order_id),
                            str(event.trade_id),
                            float(event.last_qty),
                            float(event.last_px),
                        ))
                    
                    elif isinstance(event, OrderRejected):
                        cur.execute("""
                            UPDATE ai_extensions.live_orders
                            SET status = 'REJECTED',
                                rejection_reason = %s,
                                rejected_at = NOW()
                            WHERE order_id = %s;
                        """, (event.reason, str(event.order_id)))
                    
                    conn.commit()
        except Exception as e:
            print(f"⚠️ Error recording order event: {e}")
    
    def on_position_event(self, event):
        """Handle position events"""
        if not self.session_id:
            return
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if isinstance(event, PositionOpened):
                        cur.execute("""
                            INSERT INTO ai_extensions.live_positions
                            (session_id, position_id, instrument_id, side, entry_price, 
                             quantity, opened_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW());
                        """, (
                            self.session_id,
                            str(event.position_id),
                            str(event.instrument_id),
                            str(event.opening_order_side),
                            float(event.entry_price) if hasattr(event, 'entry_price') else 0.0,
                            float(event.quantity),
                        ))
                    
                    elif isinstance(event, PositionChanged):
                        cur.execute("""
                            UPDATE ai_extensions.live_positions
                            SET quantity = %s,
                                unrealized_pnl = %s,
                                updated_at = NOW()
                            WHERE position_id = %s;
                        """, (
                            float(event.quantity),
                            float(event.unrealized_pnl.as_double()) if hasattr(event, 'unrealized_pnl') else 0.0,
                            str(event.position_id),
                        ))
                    
                    elif isinstance(event, PositionClosed):
                        cur.execute("""
                            UPDATE ai_extensions.live_positions
                            SET realized_pnl = %s,
                                closed_at = NOW()
                            WHERE position_id = %s;
                        """, (
                            float(event.realized_pnl.as_double()) if hasattr(event, 'realized_pnl') else 0.0,
                            str(event.position_id),
                        ))
                    
                    conn.commit()
        except Exception as e:
            print(f"⚠️ Error recording position event: {e}")
    
    def stop(self):
        """Stop monitoring and close session"""
        if self.session_id:
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE ai_extensions.live_sessions
                            SET status = 'STOPPED',
                                stopped_at = NOW()
                            WHERE id = %s;
                        """, (self.session_id,))
                        conn.commit()
                print("✅ Live trading session stopped")
            except Exception as e:
                print(f"⚠️ Error stopping session: {e}")
