#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pickle
import config
import requests
from bs4 import BeautifulSoup


class Tutsplus:

    SIGNIN_URL = "https://tutsplus.com/sign_in"
    SIGNIN_POST_URL = "https://tutsplus.com/sessions"
    LOGIN_SUCCESS_URL = "https://tutsplus.com/account/courses"

    def __init__(self):
        self.user = config.USER
        self.password = config.PASSWORD
        self.download_path = config.DOWNLOAD_PATH
        self.s = self.get_session()

    def get_session(self):
        s = self._load_session()
        if self.check_login(s):
            return s
        else:
            return self.get_login_session()

    def _load_session(self):
        if not os.path.exists('session.pkl'):
            return requests.session()
        with open('session.pkl', 'rb') as f:
            return pickle.load(f)

    def _dump_session(self, session):
        with open('session.pkl', 'wb') as f:
            pickle.dump(session, f)

    def check_login(self, session):
        check = session.get(self.LOGIN_SUCCESS_URL)
        if check.url == self.LOGIN_SUCCESS_URL:
            return True
        else:
            return False

    def get_login_session(self):
        s = requests.session()
        signin_source = s.get(self.SIGNIN_URL).content
        soup = BeautifulSoup(signin_source)
        authenticity_token = soup.find(
            attrs={"name": "authenticity_token"})['value']
        data = {
            "authenticity_token": authenticity_token,
            "session[login]": self.user,
            "session[password]": self.password
        }
        r = s.post(self.SIGNIN_POST_URL, data=data)
        
        if self.check_login(s):
            print 'login success'
            self._dump_session(s)
            return s
        else:
            sys.exit('Sorry, login failed, I can do nothing...')

    def _request_content(self, url):
        return self.s.get(url).content

    def download_courses(self, course_list):
        for c in course_list:
            self.download_course(c)

    def download_course(self, course_url):
        course_info = self._get_course_info(course_url)
        course_title = course_info["title"]
        course_folder = os.path.expanduser(
            os.path.join(self.download_path, course_title))
        if not os.path.exists(course_folder):
            os.makedirs(course_folder)
        for chapter in course_info["chapters"]:
            self._down_chapter(chapter, course_folder)
        if course_info["source_file"]:
            self._down_file(course_info["source_file"],
                            "SourceFils.zip", course_folder)

    def _get_course_info(self, course_url):
        chapters = []
        source = self._request_content(course_url)
        soup = BeautifulSoup(source)
        course_title = soup.select(".course__title")[0].get_text()
        course_source_file = None
        dl = soup.select(".course__download-link")
        if dl:
            course_source_file = [0].get("href")

        self.token = soup.find(attrs={"name": "csrf-token"}).get("content")
        chapters_dom_list = soup.select(".lesson-index__chapter")
        for c in chapters_dom_list:
            lessons = []
            val = [text.replace(':', '_') for text in c.stripped_strings]
            chapter_title = "{0} {1}({2})".format(
                val[0], 
                "".join(i for i in val[1] if i not in '\\/:*?\"<>|'), 
                val[2])
            next_sibling = c.nextSibling
            while next_sibling.name == "h3":
                txt = [t.replace(':', '_')
                       for t in next_sibling.stripped_strings]
                lesson_title = "{0} {1}({2})".format(
                    txt[0], 
                    "".join(i for i in txt[1] if i not in '\\/:*?\"<>|'), 
                    txt[2])
                lesson_download_link = next_sibling.select(
                    ".lesson-index__download-link")[0].get("href")
                lesson = {"title": lesson_title, "link": lesson_download_link}
                lessons.append(lesson)
                next_sibling = next_sibling.nextSibling
            chapter = {"chapterTitle": chapter_title, "lessons": lessons}
            chapters.append(chapter)
        return {"title": course_title, "chapters": chapters, "source_file": course_source_file}

    def _down_chapter(self, chapter, course_folder):
        chapter_title = chapter["chapterTitle"]
        chapter_folder = os.path.join(course_folder, chapter_title)
        if not os.path.exists(chapter_folder):
            os.makedirs(chapter_folder)
        print "Downloading chapter: " + chapter_title
        for l in chapter["lessons"]:
            self._down_file(l["link"], l["title"], chapter_folder)

    def _down_file(self, url, name, folder):
        save_file_name = os.path.join(folder, name + ".mp4")
        h = {
            "content-type": "application/x-www-form-urlencoded",
            "content-length": "78",
            "Host": "courses.tutsplus.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.137 Safari/537.36"
        }
        data = {"authenticity_token": self.token}
        r = self.s.post(url, headers=h, data=data)
        real_file_url = r.url
        print "Downloading File:" + real_file_url
        res = requests.get(real_file_url, stream=True)
        if not res.status_code == 200:
            print "Can not download file:" + real_file_url
            return
        try:
            os.remove(save_file_name)
        except OSError:
            pass

        with open(save_file_name, "wb") as f:
            for chunk in res.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    f.flush()
        print "File:" + real_file_url + " download completed!"


if __name__ == '__main__':
    if len(sys.argv) > 1:
        t = Tutsplus()
        t.download_courses(sys.argv[1:])
