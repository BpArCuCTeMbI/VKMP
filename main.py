import os
import re
import json
import html
import getpass
import datetime
import argparse
from sys import platform

import requests

if platform == 'win32':
    # pylint: disable=import-error
    import wincertstore


DUMP_FILE = 'dump'


def usage():
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', '-e', help='Login email')
    parser.add_argument('--password', '-p', help='Login Password')
    parser.add_argument('--tracks-num', '-n', metavar='N', type=int, help='Number of tracks to fetch')
    parser.add_argument('--csv', help='Get dump in csv format', action='store_true')
    return parser.parse_args()


def get_track_row(name, performer, time, row_format='raw'):
    """
    function to get track row in specified format
    """
    if row_format == 'csv':
        return '"{}","{}","{}"\n'.format(name, performer, time)
    return '{0:<60} - {1:<60}{2:<60}\n'.format(name, performer, time)


def getFormAction(html: 'html code with some <form>') -> str:
    """
    function to get the urls for authorization and 2FA requests
    """
    form_action = re.findall(r'<form(?= ).* action="(.+)"', html)
    if form_action:
        return form_action[0]
    return None

# def getTwoFactorAction(html: 'html code with two-factor auth form') -> str:
#	"""
#	function to get the url for two-factor auth request
#	"""
#	TFA_url = re.findall(r'<form(?= ).* action="(.+)"', html)
#	if TFA_url:
#		return TFA_url[0]


###########################################################################
session = requests.Session()
user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
user_agent2 = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36'
urlAudioPHP = 'https://vk.com/al_audio.php'

getHeaders = {
    'User-Agent': user_agent
}


def fetch_ssl_certificate():
    """
    function to add system CAs for cert checking
    """

    if platform == 'linux':
        print('OS: Linux; changing certs environment variable...')
        os.environ['REQUESTS_CA_BUNDLE'] = os.path.join('/etc/ssl/certs', 'ca-certificates.crt')
        print('Certs env variable changed: REQUESTS_CA_BUNDLE={0}'.format(os.getenv('REQUESTS_CA_BUNDLE')))

    # if you're on WINDOWS, it probably should work for you. Extracting
    if platform == 'win32':
        print('OS: Windows; extracting SSL certificates')
        file = open('./certs_extracted', 'w')
        for storename in ['CA', 'ROOT']:
            with wincertstore.CertSystemStore(storename) as store:
                for cert in store.itercerts(usage=wincertstore.SERVER_AUTH):
                    pem = cert.get_pem()
                    file.write(pem + '\n')
        file.close()
        os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'certs_extracted')
        print('Certificates extracted. Certs env variable changed: REQUESTS_CA_BUNDLE={0}'.format(os.getenv('REQUESTS_CA_BUNDLE')))


def login_vk(email, password):
    """
    logging in from mobile version of VK (it's cleaner)
    """
    loginUrl = 'https://m.vk.com'
    loginHTML = session.get(loginUrl)
    print('Getting HTML of m.vk.com login page... ', loginHTML)

    loginFormAction = getFormAction(loginHTML.text)
    if not loginFormAction:
        if platform == 'win32':
            os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
        raise Exception('Login link is not found, probably vk changed login flow')

    loginFormData = {
        'email': email,
        'pass': password
    }

    loginResponse = session.post(loginFormAction, loginFormData)
    print('Trying to log in... ', loginResponse)
    match = re.search('authcheck', loginResponse.text)
    if match:
        print('Two-factor authentication is enabled.')

        TFA_url = 'https://m.vk.com' + getFormAction(loginResponse.text)
        if TFA_url == 'https://m.vk.com':
            if platform == 'win32':
                os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
            raise Exception('Failed to get 2FA url for auth request')

        # print(TFA_url)
        TFA_code = input('Enter the 2FA code from your authenticator app or VK support private message: ')
        TFAFormData = {
            '_ajax': '1',
            'code': TFA_code
        }
        TFAHeaders = {
            'User-Agent': user_agent,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        TFA_responce = session.post(TFA_url, headers=TFAHeaders, data=TFAFormData)
        print('Sending POST with 2FA... ', TFA_responce)


def get_vk_hash(response_text):
    match = re.search(r'(hash)=([a-zA-Z0-9]*)', response_text)
    if match is None:
        if platform == 'win32':
            os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
        raise Exception('Failed to get vk hash: bad login or vk html markup was changed')
    vk_hash = match.group(2)
    print('HASH is: ' + vk_hash)
    return vk_hash


def get_user_id(response_text):
    match = re.search(r'\"id\":([0-9]{1,9}),', response_text)
    if match is None:
        if platform == 'win32':
            os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
        raise Exception('Failed to get user id, probably vk html markup changed')
    owner_id = match.group(1)
    print('User id: ' + owner_id)
    return owner_id


def fetch_tracks(owner_id, maxAudioNumber):
    offset = 0
    headers = {
        'User-Agent': user_agent2,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest'
    }
    data = {
        'act': 'load_section',
        'al': '1',
        'claim': '0',
        'offset': str(offset),
        'playlist_id': '-1',
        'type': 'playlist',
        'track_type': 'default',
        'owner_id': owner_id
    }

    tracks = []

    while offset < maxAudioNumber:

        data['offset'] = str(offset)

        rs = session.post(urlAudioPHP, headers=headers, data=data)
        print('Sending POST to al_audio.php... ', rs, 'CURRENT OFFSET=', offset)

        #raw_response = rs.text

        #match = re.search(r'\{(.*)\}', raw_response)
        #cleanJSON = match.group(0)

        #f = open('./raw_response', 'w')
        # f.write(raw_response)
        # f.close()
        #f = open('./clean_json', 'w')
        # f.write(cleanJSON)

        parsedJSON = json.loads(rs.text)
        if not parsedJSON['payload'][1]:
            break  # exit on empty payload
        lst = parsedJSON['payload'][1][0]['list']

        added_tracks = 0
        for i, _ in enumerate(lst):
            name = html.unescape(lst[i][4])
            performer = html.unescape(lst[i][3])
            time = str(datetime.timedelta(seconds=lst[i][5]))
            track = (name, performer, time)
            if track not in tracks:
                added_tracks += 1
                tracks.append(track)
        if added_tracks == 0:
            break  # exit on recursive offset

        offset += len(lst)
    return tracks


def dump_tracks(tracks: list, file=DUMP_FILE, dumpFormat='raw'):
    with open(file, 'w', encoding='utf-8') as f:
        if dumpFormat == 'csv':
            f.write('name,performer,time\n')
        for name, performer, time in tracks:
            track = get_track_row(name, performer, time, row_format=dumpFormat)
            f.write(track)
    print('Tracks written to ./{}: '.format(file), len(tracks))


def main(args=None):

    # if you get some SSL errors, it's likely you have issues with Certificate Authority file.
    # To fix this usually you need to provide a proper CA file to this program.
    # If you're on LINUX, your system usually has actual file - just google its location
    # and set the REQUESTS_CA_BUNDLE env variable in the next line:
    fetch_ssl_certificate()

    ###################################################################################
    maxAudioNumber = args and args.tracks_num or int(input('enter the number of tracks on your account (see your profile page): '))
    email = args and args.email or input('email: ')
    password = args and args.password or getpass.getpass('password: ')
    dumpFormat = 'csv' if args and args.csv else 'raw'

    ######################################################################################
    login_vk(email, password)
    #######################################################################################
    # vk hash and owner_id are user specific
    # get vk hash (is not used now, probably will be used later)
    rs = session.get('https://vk.com', headers=getHeaders)
    vk_hash = get_vk_hash(rs.text)
    owner_id = get_user_id(rs.text)

    #######################################################################################
    tracks = fetch_tracks(owner_id, maxAudioNumber)
    #######################################################################################
    dump_tracks(tracks, dumpFormat=dumpFormat)

    if platform == 'win32':
        os.remove(os.getenv('REQUESTS_CA_BUNDLE'))


if __name__ == '__main__':
    args = usage()
    main(args)
