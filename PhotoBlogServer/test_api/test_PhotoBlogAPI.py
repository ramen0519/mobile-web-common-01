import unittest

import requests

from PhotoBlogAPI import PhotoBlogAPI

HOST = 'http://127.0.0.1:8000'
USERNAME = 'admin'
PASSWORD = '1234'
IMAGE = '../media/images/pig.png'


class PhotoBlogAPITest(unittest.TestCase):
    def setUp(self):
        self.api = PhotoBlogAPI(HOST)
        self.api.get_token(USERNAME, PASSWORD)

    def test_token(self):
        token = self.api.get_token(USERNAME, PASSWORD)
        self.assertEqual(len(token), 40)

    def test_wrong_password(self):
        with self.assertRaises(requests.HTTPError):
            self.api.get_token(USERNAME, 'wrong password')

    def test_methods(self):
        methods = self.api.get_methods()
        for method in ['GET', 'POST', 'HEAD', 'OPTIONS']:
            self.assertIn(method, methods)

    def test_get_posts(self):
        posts = self.api.get_posts()
        self.assertIsInstance(posts, list)

    def test_post_format(self):
        for post in self.api.get_posts():
            self.assertEqual(self.api.check_post(post), [])

    def test_image(self):
        for post in self.api.get_posts():
            self.assertTrue(self.api.check_image(post['image']))

    def test_image_not_found(self):
        self.assertFalse(self.api.check_image(HOST + '/media/images/no_image.png'))

    def test_upload(self):
        data = {'author': 1, 'title': 'API 자동 테스트', 'text': '테스트 코드로 올린 글',
                'created_date': '2026-10-19T12:00:00+09:00', 'published_date': '2026-10-19T12:00:00+09:00'}
        res = self.api.upload(data, IMAGE)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.api.check_post(res.json()), [])

        titles = [post['title'] for post in self.api.get_posts()]
        self.assertIn('API 자동 테스트', titles)

    def test_upload_without_author(self):
        data = {'title': 'author 없음', 'text': '업로드 실패해야 함'}
        res = self.api.upload(data, IMAGE)
        self.assertEqual(res.status_code, 400)

    def test_check_wrong_post(self):
        post = {'author': '1', 'title': '', 'text': None, 'created_date': 'yesterday',
                'published_date': '2024-13-01', 'image': 'images/pig.png'}
        errors = self.api.check_post(post)
        self.assertEqual(len(errors), 6)

    def test_check_long_title(self):
        post = {'author': 1, 'title': 'a' * 201, 'text': '', 'created_date': '2024-06-03T18:34:00+09:00',
                'published_date': None, 'image': 'http://127.0.0.1:8000/media/images/pig.png'}
        self.assertEqual(self.api.check_post(post), ['title이 200자를 넘음'])

    def test_check_missing_field(self):
        errors = self.api.check_post({'title': '제목만 있음'})
        self.assertIn('image 없음', errors)
        self.assertNotIn('title 없음', errors)


if __name__ == '__main__':
    unittest.main()
