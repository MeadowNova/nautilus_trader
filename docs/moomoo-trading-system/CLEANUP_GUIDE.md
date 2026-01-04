# Documentation Consolidation - Cleanup Guide

This guide identifies old/scattered documentation files that can now be safely removed after consolidation.

## Summary

**New consolidated documentation:** `/home/ajk/Nautilus/nautilus_trader/docs/moomoo-trading-system/`

- 10 comprehensive documentation files
- 5,663 lines of documentation
- ~150KB total size
- Complete coverage of all aspects

## Files Safe to Remove

### 1. Temporary Fix Files (Should be deleted)

**Priority:** HIGH - These were temporary fixes, now integrated into codebase

```bash
# Delete temporary fix files
rm /home/ajk/Nautilus/MOOMOO_FIXES_PRIORITY1.py
rm /home/ajk/Nautilus/MOOMOO_FIXES_PRIORITY2_AND_3.md
```

**Rationale:**
- MOOMOO_FIXES_PRIORITY1.py: Reconciliation methods are now implemented in `nautilus_trader/adapters/moomoo/execution.py`
- MOOMOO_FIXES_PRIORITY2_AND_3.md: Fixes documented in CHANGELOG.md and TROUBLESHOOTING.md

### 2. Duplicate Documentation Files (Can be archived or removed)

**Priority:** MEDIUM - Content consolidated into new structure

```bash
# Create archive directory
mkdir -p /home/ajk/Nautilus/docs_archive

# Move old docs to archive
mv /home/ajk/Nautilus/PROJECT_MOOMOO_RL_TRADING.md /home/ajk/Nautilus/docs_archive/
mv /home/ajk/Nautilus/MOOMOO_TRADING_ANALYSIS.md /home/ajk/Nautilus/docs_archive/
mv /home/ajk/Nautilus/nautilus_trader/docs/MOOMOO_RL_PAPER_TRADING_GUIDE.md /home/ajk/Nautilus/docs_archive/
mv /home/ajk/Nautilus/plans/moomoo-rl-paper-trading-system.md /home/ajk/Nautilus/docs_archive/
```

**Rationale:**
- PROJECT_MOOMOO_RL_TRADING.md: Summary now in README.md
- MOOMOO_TRADING_ANALYSIS.md: Analysis now in STRATEGIES.md
- docs/MOOMOO_RL_PAPER_TRADING_GUIDE.md: Superseded by QUICKSTART.md + SETUP.md
- plans/moomoo-rl-paper-trading-system.md: Implemented, documented in ARCHITECTURE.md

**Or delete entirely:**
```bash
# If you don't want to keep archives
rm /home/ajk/Nautilus/PROJECT_MOOMOO_RL_TRADING.md
rm /home/ajk/Nautilus/MOOMOO_TRADING_ANALYSIS.md
rm /home/ajk/Nautilus/nautilus_trader/docs/MOOMOO_RL_PAPER_TRADING_GUIDE.md
rm /home/ajk/Nautilus/plans/moomoo-rl-paper-trading-system.md
```

### 3. Old Paper Trading Runbook (Optional to keep)

**Priority:** LOW - May be useful for other systems

```bash
# Keep if you have other paper trading systems
# Otherwise archive:
mv /home/ajk/Nautilus/nautilus_trader/ai-working/paper_trading/runbook/ /home/ajk/Nautilus/docs_archive/
```

**Rationale:**
- General paper trading guide (not Moomoo-specific)
- QUICKSTART.md now provides Moomoo-specific quickstart

## Cleanup Script

Run this to perform all cleanup at once:

```bash
#!/bin/bash
# cleanup_old_docs.sh

set -e

cd /home/ajk/Nautilus

echo "Creating archive directory..."
mkdir -p docs_archive

echo "Removing temporary fix files..."
rm -f MOOMOO_FIXES_PRIORITY1.py
rm -f MOOMOO_FIXES_PRIORITY2_AND_3.md

echo "Archiving old documentation..."
mv PROJECT_MOOMOO_RL_TRADING.md docs_archive/ 2>/dev/null || true
mv MOOMOO_TRADING_ANALYSIS.md docs_archive/ 2>/dev/null || true
mv nautilus_trader/docs/MOOMOO_RL_PAPER_TRADING_GUIDE.md docs_archive/ 2>/dev/null || true
mv plans/moomoo-rl-paper-trading-system.md docs_archive/ 2>/dev/null || true

echo "Cleanup complete!"
echo "Archived files in: docs_archive/"
echo "New documentation at: nautilus_trader/docs/moomoo-trading-system/"

# Optional: Create README in archive
cat > docs_archive/README.txt <<EOF
Archived Moomoo Trading System Documentation
===========================================

These files were superseded by consolidated documentation at:
/home/ajk/Nautilus/nautilus_trader/docs/moomoo-trading-system/

Archived on: $(date)

Contents:
- PROJECT_MOOMOO_RL_TRADING.md - Original project summary
- MOOMOO_TRADING_ANALYSIS.md - Initial analysis
- MOOMOO_RL_PAPER_TRADING_GUIDE.md - First setup guide
- moomoo-rl-paper-trading-system.md - Implementation plan

All content has been integrated into the new documentation structure.
EOF

echo "Created archive README"
```

## Files to KEEP

**Do NOT remove these:**

```
/home/ajk/Nautilus/nautilus_trader/
├── scripts/start_paper_trading_moomoo.py         # Main entry point
├── nautilus_trader/adapters/moomoo/              # Moomoo adapter (all files)
├── ajk_strategies/rl_strategies/                 # RL strategies
├── ajk_strategies/rl_framework/                  # RL framework
├── logs/*.log                                     # Trading logs
├── models/*.pt                                    # RL model checkpoints
└── docs/moomoo-trading-system/                   # New documentation ✓

/home/ajk/Nautilus/nautilus_trader/.serena/memories/
└── moomoo_adapter_fixes_2025_12_09.md           # Fix history (for Serena)
```

## Verification After Cleanup

Check that new documentation is accessible:

```bash
# Verify all files exist
ls -lh /home/ajk/Nautilus/nautilus_trader/docs/moomoo-trading-system/

# Should show:
# - README.md
# - QUICKSTART.md
# - SETUP.md
# - CONFIGURATION.md
# - STRATEGIES.md
# - MONITORING.md
# - TROUBLESHOOTING.md
# - ARCHITECTURE.md
# - API_REFERENCE.md
# - CHANGELOG.md

# Test that links work
cd /home/ajk/Nautilus/nautilus_trader/docs/moomoo-trading-system
cat README.md | grep -o '\[.*\.md\]' | sort -u
```

## Documentation Migration Map

| Old File | New Location | Status |
|----------|--------------|--------|
| MOOMOO_FIXES_PRIORITY1.py | TROUBLESHOOTING.md § Reconciliation Methods | ✓ Integrated |
| MOOMOO_FIXES_PRIORITY2_AND_3.md | TROUBLESHOOTING.md + CHANGELOG.md | ✓ Integrated |
| PROJECT_MOOMOO_RL_TRADING.md | README.md + ARCHITECTURE.md | ✓ Superseded |
| MOOMOO_TRADING_ANALYSIS.md | STRATEGIES.md | ✓ Superseded |
| docs/MOOMOO_RL_PAPER_TRADING_GUIDE.md | QUICKSTART.md + SETUP.md + CONFIGURATION.md | ✓ Superseded |
| plans/moomoo-rl-paper-trading-system.md | ARCHITECTURE.md + SETUP.md | ✓ Superseded |
| ai-working/paper_trading/runbook/README.md | QUICKSTART.md (Moomoo-specific) | Partially superseded |

## Post-Cleanup Actions

1. **Update README.md in project root:**
   ```bash
   # Add link to new documentation
   echo "## Moomoo Trading System Documentation" >> /home/ajk/Nautilus/README.md
   echo "" >> /home/ajk/Nautilus/README.md
   echo "Complete documentation: [docs/moomoo-trading-system/](nautilus_trader/docs/moomoo-trading-system/README.md)" >> /home/ajk/Nautilus/README.md
   ```

2. **Update any hardcoded paths:**
   ```bash
   # Search for references to old docs
   grep -r "MOOMOO_RL_PAPER_TRADING_GUIDE" /home/ajk/Nautilus/nautilus_trader/ --exclude-dir=.git
   grep -r "PROJECT_MOOMOO_RL_TRADING" /home/ajk/Nautilus/ --exclude-dir=.git
   ```

3. **Test documentation links:**
   ```bash
   cd /home/ajk/Nautilus/nautilus_trader/docs/moomoo-trading-system
   # Use a markdown link checker or manually verify links work
   ```

## Disk Space Recovered

Approximate space recovered:

```
MOOMOO_FIXES_PRIORITY1.py:               ~7 KB
MOOMOO_FIXES_PRIORITY2_AND_3.md:         ~5 KB
PROJECT_MOOMOO_RL_TRADING.md:            ~5 KB
MOOMOO_TRADING_ANALYSIS.md:              ~3 KB
MOOMOO_RL_PAPER_TRADING_GUIDE.md:        ~11 KB
moomoo-rl-paper-trading-system.md:       ~8 KB
---------------------------------------------------
Total:                                   ~39 KB

New consolidated documentation:          ~150 KB
Net increase:                            ~111 KB
```

The slight increase is worthwhile because:
- All content in one organized location
- Comprehensive troubleshooting guide
- Better navigation and cross-references
- Single source of truth

---

**Recommendation:** Run the cleanup script to archive old docs and keep your repository clean.

**Before running:**
- Backup important data
- Commit current state to git
- Review archived files one more time

**After cleanup:**
- Update any bookmarks to point to new docs
- Notify team members of new documentation location
- Update CI/CD scripts if they reference old paths
