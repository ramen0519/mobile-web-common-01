# PhotoBlogAPI.py
# 포토 블로그 REST API 검증 엔진
from datetime import datetime

import requests


class PhotoBlogAPI(object):
    """포토 블로그 REST API 검증"""
    FIELDS = ('author', 'title', 'text', 'created_date', 'published_date', 'image')

    def __init__(self, host):
        self.host = host
        self.headers = {'Accept': 'application/json'}

    def get_token(self, username, password):
        """아이디, 비밀번호로 토큰을 받아서 요청 헤더에 넣는다."""
        res = requests.post(self.host + '/api-token-auth/', {'username': username, 'password': password})
        res.raise_for_status()
        token = res.json()['token']
        self.headers['Authorization'] = 'Token ' + token
        return token

    def get_methods(self):
        """API로 사용 가능한 메소드 목록 (Allow 헤더)"""
        res = requests.options(self.host + '/api_root/Post/', headers=self.headers)
        return [method.strip() for method in res.headers['Allow'].split(',')]

    def get_posts(self):
        """게시물 목록 획득 (JSON Array)"""
        res = requests.get(self.host + '/api_root/Post/', headers=self.headers)
        res.raise_for_status()
        return res.json()

    def upload(self, data, image_path):
        """게시물 업로드 (Multipart : Text + Image)"""
        with open(image_path, 'rb') as file:
            res = requests.post(self.host + '/api_root/Post/', data=data, files={'image': file}, headers=self.headers)
        return res

    def check_post(self, post):
        """게시물 하나의 형식을 검사해서 잘못된 점을 리스트로 돌려준다. (빈 리스트면 정상)"""
        errors = []
        for field in self.FIELDS:
            if field not in post:
                errors.append(field + ' 없음')
        if errors:
            return errors

        if not isinstance(post['author'], int):
            errors.append('author는 숫자여야 함')
        if not isinstance(post['title'], str) or post['title'] == '':
            errors.append('title이 비어 있음')
        elif len(post['title']) > 200:
            errors.append('title이 200자를 넘음')
        if not isinstance(post['text'], str):
            errors.append('text는 문자열이어야 함')
        if not self.is_datetime(post['created_date']):
            errors.append('created_date 형식이 잘못됨')
        if post['published_date'] is not None and not self.is_datetime(post['published_date']):
            errors.append('published_date 형식이 잘못됨')
        if not str(post['image']).startswith(('http://', 'https://')):
            errors.append('image가 URL이 아님')
        return errors

    def is_datetime(self, value):
        """날짜 형식 확인 (예: 2024-06-03T18:34:00+09:00)"""
        try:
            datetime.fromisoformat(value)
            return True
        except (TypeError, ValueError):
            return False

    def check_image(self, url):
        """이미지 URL로 실제 이미지를 받을 수 있는지 확인"""
        res = requests.get(url)
        return res.status_code == 200 and res.headers.get('Content-Type', '').startswith('image/')
