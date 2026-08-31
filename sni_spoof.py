#!/usr/bin/env python3
import ssl
import socket


def create_spoofed_context(target_host, spoof_host="www.google.com"):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context, spoof_host


def test_sni_spoof(vpn_host, vpn_port=443):
    context, sni = create_spoofed_context(vpn_host)
    
    sock = socket.create_connection((vpn_host, vpn_port), timeout=10)
    
    with context.wrap_socket(sock, server_hostname=sni) as ssock:
        cert = ssock.getpeercert()
        cipher = ssock.cipher()
        print(f"Connected to {vpn_host} with SNI={sni}")
        print(f"Cipher: {cipher}")
        return True


if __name__ == '__main__':
    test_sni_spoof("your-vpn-server.com")
