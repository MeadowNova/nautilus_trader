import socket


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    port = 12312

    sock.connect((host, port))
    sock.send(b"Hello server!")

    with open("Received_file", "wb") as out_file:
        print("File opened")
        print("Receiving data...")
        while True:
            data = sock.recv(1024)
            if not data:
                break
            out_file.write(data)

    print("Successfully received the file")
    sock.close()
    print("Connection closed")


if __name__ == "__main__":
    main()

======================

def send_file(filename: str = "mytext.txt", testing: bool = False) -> None:
    import socket

    port = 12312  # Reserve a port for your service.
    sock = socket.socket()  # Create a socket object
    host = socket.gethostname()  # Get local machine name
    sock.bind((host, port))  # Bind to the port
    sock.listen(5)  # Now wait for client connection.

    print("Server listening....")

    while True:
        conn, addr = sock.accept()  # Establish connection with client.
        print(f"Got connection from {addr}")
        data = conn.recv(1024)
        print(f"Server received: {data = }")

        with open(filename, "rb") as in_file:
            data = in_file.read(1024)
            while data:
                conn.send(data)
                print(f"Sent {data!r}")
                data = in_file.read(1024)

        print("Done sending")
        conn.close()
        if testing:  # Allow the test to complete
            break

    sock.shutdown(1)
    sock.close()


if __name__ == "__main__":
    send_file()

==========================

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "beautifulsoup4",
#     "httpx",
# ]
# ///

import httpx
from bs4 import BeautifulSoup

"""
Get the HTML code of finance yahoo and select the current qsp-price
Current AAPL stock price is   228.43
Current AMZN stock price is   201.85
Current IBM  stock price is   210.30
Current GOOG stock price is   177.86
Current MSFT stock price is   414.82
Current ORCL stock price is   188.87
"""


def stock_price(symbol: str = "AAPL") -> str:
    """
    >>> stock_price("EEEE")
    'No <fin-streamer> tag with the specified data-testid attribute found.'
    >>> isinstance(float(stock_price("GOOG")),float)
    True
    """
    url = f"https://finance.yahoo.com/quote/{symbol}?p={symbol}"
    yahoo_finance_source = httpx.get(
        url, headers={"USER-AGENT": "Mozilla/5.0"}, timeout=10, follow_redirects=True
    ).text
    soup = BeautifulSoup(yahoo_finance_source, "html.parser")

    if specific_fin_streamer_tag := soup.find("span", {"data-testid": "qsp-price"}):
        return specific_fin_streamer_tag.get_text()
    return "No <fin-streamer> tag with the specified data-testid attribute found."


# Search for the symbol at https://finance.yahoo.com/lookup
if __name__ == "__main__":
    from doctest import testmod

    testmod()

    for symbol in "AAPL AMZN IBM GOOG MSFT ORCL".split():
        print(f"Current {symbol:<4} stock price is {stock_price(symbol):>8}")


====================================
