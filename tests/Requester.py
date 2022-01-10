############################ Copyrights and license ############################
#                                                                              #
# Copyright 2022 Enrico Minack <github@enrico.minack.dev>                      #
#                                                                              #
# This file is part of PyGithub.                                               #
# http://pygithub.readthedocs.io/                                              #
#                                                                              #
# PyGithub is free software: you can redistribute it and/or modify it under    #
# the terms of the GNU Lesser General Public License as published by the Free  #
# Software Foundation, either version 3 of the License, or (at your option)    #
# any later version.                                                           #
#                                                                              #
# PyGithub is distributed in the hope that it will be useful, but WITHOUT ANY  #
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS    #
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more #
# details.                                                                     #
#                                                                              #
# You should have received a copy of the GNU Lesser General Public License     #
# along with PyGithub. If not, see <http://www.gnu.org/licenses/>.             #
#                                                                              #
################################################################################
import datetime

import mock

import github

from . import Framework

REPO_NAME = "PyGithub/PyGithub"


class RequesterUnThrottled(Framework.TestCase):
    seconds_between_requests = None
    seconds_between_writes = None
    per_page = 10

    def testShouldNotDeferRequests(self):
        with mock.patch("github.Requester.time.sleep") as sleep_mock:
            # same test setup as in RequesterThrottled.testShouldDeferRequests
            repository = self.g.get_repo(REPO_NAME)
            releases = [release for release in repository.get_releases()]
            self.assertEqual(len(releases), 30)
        sleep_mock.assert_not_called()


class RequesterThrottled(Framework.TestCase):
    seconds_between_requests = 1.0
    seconds_between_writes = 3.0
    per_page = 10

    def testShouldDeferRequests(self):
        now = [datetime.datetime.utcnow()]

        def sleep(seconds):
            now[0] = now[0] + datetime.timedelta(seconds=seconds)

        def utcnow():
            return now[0]

        with mock.patch("github.Requester.time.sleep", side_effect=sleep) as sleep_mock, \
                mock.patch("github.Requester.datetime") as datetime_mock:
            datetime_mock.utcnow = utcnow

            # same test setup as in RequesterUnThrottled.testShouldNotDeferRequests
            repository = self.g.get_repo(REPO_NAME)
            releases = [release for release in repository.get_releases()]
            self.assertEqual(len(releases), 30)

        self.assertEqual(
            sleep_mock.call_args_list,
            [mock.call(1), mock.call(1), mock.call(1)]
        )

    def testShouldDeferWrites(self):
        now = [datetime.datetime.utcnow()]

        def sleep(seconds):
            now[0] = now[0] + datetime.timedelta(seconds=seconds)

        def utcnow():
            return now[0]

        with mock.patch("github.Requester.time.sleep", side_effect=sleep) as sleep_mock, \
                mock.patch("github.Requester.datetime") as datetime_mock:
            datetime_mock.utcnow = utcnow

            # same test setup as in AuthenticatedUser.testEmail
            user = self.g.get_user()
            emails = user.get_emails()
            self.assertEqual(
                [item.email for item in emails],
                ["vincent@vincent-jacques.net", "github.com@vincent-jacques.net"],
            )
            self.assertTrue(emails[0].primary)
            self.assertTrue(emails[0].verified)
            self.assertEqual(emails[0].visibility, "private")
            user.add_to_emails("1@foobar.com", "2@foobar.com")
            self.assertEqual(
                [item.email for item in user.get_emails()],
                [
                    "vincent@vincent-jacques.net",
                    "1@foobar.com",
                    "2@foobar.com",
                    "github.com@vincent-jacques.net",
                ],
            )
            user.remove_from_emails("1@foobar.com", "2@foobar.com")
            self.assertEqual(
                [item.email for item in user.get_emails()],
                ["vincent@vincent-jacques.net", "github.com@vincent-jacques.net"],
            )

        self.assertEqual(
            sleep_mock.call_args_list,
            [
                # g.get_user() does not call into GitHub API
                # user.get_emails() is the first request so no waiting needed
                mock.call(1),  # user.add_to_emails is a write request, this is the first write request
                mock.call(1),  # user.get_emails() is a read request
                mock.call(2),  # user.remove_from_emails is a write request, it has to be 3 seconds after the last write
                mock.call(1),  # user.get_emails() is a read request
            ]
        )
