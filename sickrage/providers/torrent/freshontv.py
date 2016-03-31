# Author: Idan Gutman
# URL: http://github.com/SiCKRAGETV/SickRage/
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import time
import traceback

import requests

import sickrage
from sickrage.core.caches import tv_cache
from sickrage.core.helpers import tryInt, bs4_parser
from sickrage.core.srsession import srSession
from sickrage.providers import TorrentProvider


class FreshOnTVProvider(TorrentProvider):
    def __init__(self):
        super(FreshOnTVProvider, self).__init__("FreshOnTV",'freshon.tv')

        self.supportsBacklog = True

        self._uid = None
        self._hash = None
        self.username = None
        self.password = None
        self.ratio = None
        self.minseed = None
        self.minleech = None
        self.freeleech = False

        self.cache = FreshOnTVCache(self)

        self.urls.update({
            'login': '{base_url}/login.php?action=makelogin'.format(base_url=self.urls['base_url']),
            'detail': '{base_url}/details.php?id=%s'.format(base_url=self.urls['base_url']),
            'search': '{base_url}/browse.php?incldead=%s&words=0&cat=0&search=%s'.format(base_url=self.urls['base_url']),
            'download': '{base_url}/download.php?id=%s&type=torrent'.format(base_url=self.urls['base_url'])
        })

        self.cookies = None

    def _checkAuth(self):

        if not self.username or not self.password:
            sickrage.srLogger.warning("[{}]: Invalid username or password. Check your settings".format(self.name))

        return True

    def _doLogin(self):
        if any(requests.utils.dict_from_cookiejar(self.session.cookies).values()):
            return True

        if self._uid and self._hash:
            requests.utils.add_dict_to_cookiejar(self.session.cookies, self.cookies)
        else:
            login_params = {'username': self.username,
                            'password': self.password,
                            'login': 'submit'}

            response = srSession(self.session, self.headers).get(self.urls['login'], post_data=login_params, timeout=30)
            if not response:
                sickrage.srLogger.warning("[{}]: Unable to connect to provider".format(self.name))
                return False

            if re.search('/logout.php', response):

                try:
                    if requests.utils.dict_from_cookiejar(self.session.cookies)['uid'] and \
                            requests.utils.dict_from_cookiejar(self.session.cookies)['pass']:
                        self._uid = requests.utils.dict_from_cookiejar(self.session.cookies)['uid']
                        self._hash = requests.utils.dict_from_cookiejar(self.session.cookies)['pass']

                        self.cookies = {'uid': self._uid,
                                        'pass': self._hash}
                        return True
                except Exception:
                    sickrage.srLogger.warning("Unable to login to provider (cookie)")
                    return False

            else:
                if re.search('Username does not exist in the userbase or the account is not confirmed yet.', response):
                    sickrage.srLogger.warning("[{}]: Invalid username or password. Check your settings".format(self.name))

                if re.search('DDoS protection by CloudFlare', response):
                    sickrage.srLogger.warning("Unable to login to provider due to CloudFlare DDoS javascript check")

                    return False

    def search(self, search_params, search_mode='eponly', epcount=0, age=0, epObj=None):

        results = []
        items = {'Season': [], 'Episode': [], 'RSS': []}

        freeleech = '3' if self.freeleech else '0'

        if not self._doLogin():
            return results

        for mode in search_params.keys():
            sickrage.srLogger.debug("Search Mode: %s" % mode)
            for search_string in search_params[mode]:

                if mode is not 'RSS':
                    sickrage.srLogger.debug("Search string: %s " % search_string)

                searchURL = self.urls['search'] % (freeleech, search_string)
                sickrage.srLogger.debug("Search URL: %s" % searchURL)
                data = srSession(self.session, self.headers).get(searchURL)
                max_page_number = 0

                if not data:
                    sickrage.srLogger.debug("No data returned from provider")
                    continue

                try:
                    with bs4_parser(data) as html:

                        # Check to see if there is more than 1 page of results
                        pager = html.find('div', {'class': 'pager'})
                        if pager:
                            page_links = pager.find_all('a', href=True)
                        else:
                            page_links = []

                        if len(page_links) > 0:
                            for lnk in page_links:
                                link_text = lnk.text.strip()
                                if link_text.isdigit():
                                    page_int = int(link_text)
                                    if page_int > max_page_number:
                                        max_page_number = page_int

                        # limit page number to 15 just in case something goes wrong
                        if max_page_number > 15:
                            max_page_number = 15
                        # limit RSS search
                        if max_page_number > 3 and mode is 'RSS':
                            max_page_number = 3
                except Exception:
                    sickrage.srLogger.error("Failed parsing provider. Traceback: %s" % traceback.format_exc())
                    continue

                data_response_list = [data]

                # Freshon starts counting pages from zero, even though it displays numbers from 1
                if max_page_number > 1:
                    for i in range(1, max_page_number):

                        time.sleep(1)
                        page_searchURL = searchURL + '&page=' + str(i)
                        page_html = srSession(self.session, self.headers).get(page_searchURL)

                        if not page_html:
                            continue

                        data_response_list.append(page_html)

                try:

                    for data in data_response_list:

                        with bs4_parser(data) as html:

                            torrent_rows = html.findAll("tr", {"class": re.compile('torrent_[0-9]*')})

                            # Continue only if a Release is found
                            if len(torrent_rows) == 0:
                                sickrage.srLogger.debug("Data returned from provider does not contain any torrents")
                                continue

                            for individual_torrent in torrent_rows:

                                # skip if torrent has been nuked due to poor quality
                                if individual_torrent.find('img', alt='Nuked') is not None:
                                    continue

                                try:
                                    title = individual_torrent.find('a', {'class': 'torrent_name_link'})['title']
                                except Exception:
                                    sickrage.srLogger.warning(
                                        "Unable to parse torrent title. Traceback: %s " % traceback.format_exc())
                                    continue

                                try:
                                    details_url = individual_torrent.find('a', {'class': 'torrent_name_link'})['href']
                                    torrent_id = int((re.match('.*?([0-9]+)$', details_url).group(1)).strip())
                                    download_url = self.urls['download'] % (str(torrent_id))
                                    seeders = tryInt(individual_torrent.find('td', {'class': 'table_seeders'}).find(
                                        'span').text.strip(), 1)
                                    leechers = tryInt(individual_torrent.find('td', {'class': 'table_leechers'}).find(
                                        'a').text.strip(), 0)
                                    # FIXME
                                    size = -1
                                except Exception:
                                    continue

                                if not all([title, download_url]):
                                    continue

                                # Filter unseeded torrent
                                if seeders < self.minseed or leechers < self.minleech:
                                    if mode is not 'RSS':
                                        sickrage.srLogger.debug(
                                            "Discarding torrent because it doesn't meet the minimum seeders or leechers: {0} (S:{1} L:{2})".format(
                                                title, seeders, leechers))
                                    continue

                                item = title, download_url, size, seeders, leechers
                                if mode is not 'RSS':
                                    sickrage.srLogger.debug("Found result: %s " % title)

                                items[mode].append(item)

                except Exception:
                    sickrage.srLogger.error("Failed parsing provider. Traceback: %s" % traceback.format_exc())

            # For each search mode sort all the items by seeders if available
            items[mode].sort(key=lambda tup: tup[3], reverse=True)

            results += items[mode]

        return results

    def seedRatio(self):
        return self.ratio


class FreshOnTVCache(tv_cache.TVCache):
    def __init__(self, provider_obj):
        tv_cache.TVCache.__init__(self, provider_obj)

        # poll delay in minutes
        self.minTime = 20

    def _getRSSData(self):
        search_params = {'RSS': ['']}
        return {'entries': self.provider.search(search_params)}
