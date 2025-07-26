import socket
import threading
import time
from .s7_protocol import S7Protocol


class S7Server:
    def __init__(self):
        self.server_socket = None
        self.pdu_length = 2048
        self.db_count = 0
        self.db_limit = 0
        self.pdu = bytearray(2048)  # Assuming max PDU size
        self.cpu_state : int = S7Protocol.S7CpuStatusRun
        self.running = False
        self.server_thread = None

    def __del__(self):
        self.stop()


    def start(self, ip: str = "0.0.0.0" , tcp_port: int = 102):
        """
        Start the server.
        :param ip: IP address to bind to
        :param tcp_port: TCP port to bind to
        """
        if self.running:
            return
            
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((ip, tcp_port))
            self.server_socket.listen(5)
            self.running = True
            
            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
        except Exception as e:
            print(f"Failed to start server: {e}")
            self.running = False

    def _server_loop(self):
        """Main server loop to accept connections"""
        while self.running and self.server_socket:
            try:
                self.server_socket.settimeout(0.5)  # Non-blocking with timeout
                client_socket, client_address = self.server_socket.accept()
                print(f"Client connected from {client_address}")
                
                # Handle client in a separate thread
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket,), 
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                continue  # Check if we should continue running
            except Exception as e:
                if self.running:
                    print(f"Server error: {e}")
                break

    def _handle_client(self, client_socket):
        """Handle a single client connection"""
        try:
            # Very basic S7 protocol handling - just respond to basic requests
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                # Echo back a simple response for testing
                # In a real implementation, this would parse S7 protocol
                response = bytearray([0x03, 0x00, 0x00, 0x16, 0x02, 0xf0, 0x80, 0xd0, 
                                    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0xc0, 0x01, 
                                    0x0a, 0xc1, 0x02, 0x01, 0x00, 0xc2, 0x02, 0x01, 0x02])
                client_socket.send(response)
                break  # Simple test server - close after first response
                
        except Exception as e:
            print(f"Client handling error: {e}")
        finally:
            client_socket.close()

    def stop(self) -> bool:
        """Stop the server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
        
        return True


