"""
Test Signal Sender for Ingest Server
=====================================

Sends test signals to the ingest server for testing.
"""

import socket
import struct
import json
from datetime import datetime
import hashlib
import hmac


class SignalTester:
    """Test client for ingest server"""
    
    def __init__(self, host='localhost', port=9000):
        self.host = host
        self.port = port
    
    def create_test_signal(
        self,
        subscription_id: str,
        sequence: int,
        symbol: str = "EURUSD",
        order_type: int = 0,  # 0=BUY, 1=SELL
        volume: float = 0.10,
        price: float = 1.10000,
        secret_key: str = "test-secret-key"
    ) -> dict:
        """
        Create a test signal packet.
        
        Note: This creates a JSON representation.
        In production, use actual Protobuf encoding.
        """
        signal = {
            "subscription_id": subscription_id,
            "sequence_number": sequence,
            "generated_at": int(datetime.utcnow().timestamp() * 1000),
            "symbol": symbol,
            "order_type": order_type,
            "volume": volume,
            "price": price,
            "stop_loss": price - 0.0050 if order_type == 0 else price + 0.0050,
            "take_profit": price + 0.0100 if order_type == 0 else price - 0.0100,
        }
        
        # Calculate HMAC signature
        payload = f"{subscription_id}|{sequence}|{signal['generated_at']}|{symbol}|{order_type}|{volume:.5f}|{price:.5f}|{signal['stop_loss']:.5f}|{signal['take_profit']:.5f}"
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        signal["signature"] = signature
        
        return signal
    
    def send_signal(self, signal: dict) -> dict:
        """
        Send signal to ingest server.
        
        Returns server response.
        """
        try:
            # Connect to server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.host, self.port))
            
            # Serialize signal to JSON (simplified - use Protobuf in production)
            signal_json = json.dumps(signal).encode('utf-8')
            
            # Send length prefix (4 bytes, big-endian) + data
            length = len(signal_json)
            sock.send(struct.pack('>I', length))
            sock.send(signal_json)
            
            # Receive response length
            response_length_bytes = sock.recv(4)
            if len(response_length_bytes) < 4:
                raise Exception("Failed to receive response length")
            
            response_length = struct.unpack('>I', response_length_bytes)[0]
            
            # Receive response data
            response_data = b''
            while len(response_data) < response_length:
                chunk = sock.recv(min(4096, response_length - len(response_data)))
                if not chunk:
                    break
                response_data += chunk
            
            # Parse response
            response = json.loads(response_data.decode('utf-8'))
            
            sock.close()
            
            return response
            
        except Exception as e:
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        """Test if server is reachable"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((self.host, self.port))
            sock.close()
            return True
        except:
            return False


def main():
    """Run test scenarios"""
    print("=" * 80)
    print("INGEST SERVER TEST CLIENT")
    print("=" * 80)
    
    tester = SignalTester()
    
    # Test 1: Connection
    print("\n[TEST 1] Testing connection...")
    if tester.test_connection():
        print("✅ Connection successful")
    else:
        print("❌ Connection failed - is the server running on port 9000?")
        return
    
    # Test 2: Send valid signal
    print("\n[TEST 2] Sending valid signal...")
    signal = tester.create_test_signal(
        subscription_id="00000000-0000-0000-0000-000000000001",
        sequence=1,
        symbol="EURUSD",
        order_type=0,  # BUY
        volume=0.10,
        price=1.10000
    )
    
    print(f"Signal: {json.dumps(signal, indent=2)}")
    
    response = tester.send_signal(signal)
    print(f"Response: {json.dumps(response, indent=2)}")
    
    if "error" not in response:
        print("✅ Signal sent successfully")
    else:
        print(f"❌ Error: {response['error']}")
    
    # Test 3: Send signal with invalid signature
    print("\n[TEST 3] Sending signal with invalid signature...")
    invalid_signal = tester.create_test_signal(
        subscription_id="00000000-0000-0000-0000-000000000001",
        sequence=2,
        secret_key="wrong-key"  # Wrong key = invalid signature
    )
    
    response = tester.send_signal(invalid_signal)
    print(f"Response: {json.dumps(response, indent=2)}")
    
    if "error" in response or response.get("status") == "rejected":
        print("✅ Invalid signature correctly rejected")
    else:
        print("⚠️ Warning: Invalid signature was accepted (security issue!)")
    
    # Test 4: Send multiple signals (load test)
    print("\n[TEST 4] Load test (100 signals)...")
    success_count = 0
    error_count = 0
    
    import time
    start_time = time.time()
    
    for i in range(100):
        signal = tester.create_test_signal(
            subscription_id="00000000-0000-0000-0000-000000000001",
            sequence=i + 10,
            price=1.10000 + (i * 0.00001)
        )
        
        response = tester.send_signal(signal)
        
        if "error" not in response:
            success_count += 1
        else:
            error_count += 1
    
    elapsed = time.time() - start_time
    throughput = 100 / elapsed
    
    print(f"✅ Completed: {success_count} success, {error_count} errors")
    print(f"📊 Throughput: {throughput:.2f} signals/second")
    print(f"⏱️  Average latency: {(elapsed / 100) * 1000:.2f}ms")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
