import os
import socket
from datetime import datetime

class SocketServer:
    def __init__(self):
        self.bufsize = 1024 # 버퍼 크기 설정
        with open('./response.bin', 'rb') as file:
            self.RESPONSE = file.read() # 응답 파일 읽기

        self.DIR_PATH = './request'
        self.createDir(self.DIR_PATH)

    def createDir(self, path):
        """디렉토리 생성"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            print("Error: Failed to create the directory.")

    def getHeaderValue(self, header, name):
        """HTTP 헤더에서 name에 해당하는 값을 찾아 반환"""
        for line in header.split(b"\r\n")[1:]:
            key, _, value = line.partition(b":")
            if key.strip().lower() == name.lower():
                return value.strip()
        return None

    def saveImage(self, header, body, filename):
        """멀티파트 데이터에서 이미지 부분을 찾아 별도 파일로 저장"""
        content_type = self.getHeaderValue(header, b"Content-Type")
        if content_type is None or b"multipart/form-data" not in content_type:
            print("multipart/form-data 요청이 아닙니다.")
            return

        # Content-Type 헤더에서 boundary 값 추출
        boundary = content_type.split(b"boundary=")[1].strip(b'"')
        delimiter = b"--" + boundary

        # boundary로 각 파트를 분리
        for part in body.split(delimiter):
            # 파트 헤더와 데이터 본문은 빈 줄로 구분됨
            part_header, _, part_data = part.partition(b"\r\n\r\n")
            if b'filename="' not in part_header:
                continue

            # 원본 파일명에서 확장자를 가져옴
            orig_name = part_header.split(b'filename="')[1].split(b'"')[0]
            ext = os.path.splitext(orig_name.decode("utf-8", "ignore"))[1] or ".bin"

            # 데이터 끝의 줄바꿈(\r\n)은 다음 boundary 앞에 붙는 구분자이므로 제거
            if part_data.endswith(b"\r\n"):
                part_data = part_data[:-2]

            image_path = os.path.join(self.DIR_PATH, filename + ext)
            with open(image_path, "wb") as file:
                file.write(part_data)
            print("Image saved:", image_path, len(part_data), "bytes")

    def run(self, ip, port):
        """서버 실행"""
        # 소켓 생성
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(10)
        print("Start the socket server...")
        print("\"Ctrl+C\" for stopping the server!\r\n")

        try:
            while True:
                # 클라이언트의 요청 대기
                clnt_sock, req_addr = self.sock.accept()
                clnt_sock.settimeout(5.0) # 타임아웃 설정 (5초)
                print("Request message...\r\n")

                response = b""
                # 여기에 구현 하세요
                try:
                    # 1. 헤더의 끝(빈 줄)이 나올 때까지 수신
                    while b"\r\n\r\n" not in response:
                        data = clnt_sock.recv(self.bufsize)
                        if not data:
                            break
                        response += data

                    # 2. Content-Length 만큼 본문을 모두 받을 때까지 수신
                    header, _, body = response.partition(b"\r\n\r\n")
                    content_length = self.getHeaderValue(header, b"Content-Length")
                    content_length = int(content_length) if content_length else 0
                    while len(body) < content_length:
                        data = clnt_sock.recv(self.bufsize)
                        if not data:
                            break
                        body += data
                        response += data
                except socket.timeout:
                    print("Timeout: 받은 데이터까지만 저장합니다.")
                    header, _, body = response.partition(b"\r\n\r\n")

                print(header.decode("utf-8", "ignore"))
                print("\r\nReceived:", len(response), "bytes")

                # 실습 1: 요청을 그대로 "년-월-일-시-분-초.bin" 파일로 저장
                filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                bin_path = os.path.join(self.DIR_PATH, filename + ".bin")
                with open(bin_path, "wb") as file:
                    file.write(response)
                print("Request saved:", bin_path)

                # 실습 2: 멀티파트로 전송 받은 이미지 데이터를 별도 파일로 저장
                self.saveImage(header, body, filename)

                # 응답 전송
                clnt_sock.sendall(self.RESPONSE)

                # 클라이언트 소켓 닫기
                clnt_sock.close()
        except KeyboardInterrupt:
            print("\r\nStop the server...")

        # 서버 소켓 닫기
        self.sock.close()

if __name__ == "__main__":
    server = SocketServer()
    server.run("127.0.0.1", 8000)
