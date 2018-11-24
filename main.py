import requests
import re
import json
import getpass
import html
import os
from sys import platform

def getFormAction(html: 'html code with some <form>') -> str:
	"""
	function to get the urls for authorization and 2FA requests	
	"""
	form_action = re.findall(r'<form(?= ).* action="(.+)"', html)
	if form_action:
		return form_action[0]

#def getTwoFactorAction(html: 'html code with two-factor auth form') -> str:
#	"""
#	function to get the url for two-factor auth request
#	"""
#	TFA_url = re.findall(r'<form(?= ).* action="(.+)"', html)
#	if TFA_url:
#		return TFA_url[0]

###########################################################################
user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
urlAudioPHP = 'https://vk.com/al_audio.php'

maxAudioNumber = int(input('enter the number of tracks on your account (see your profile page): '))
##########################################################################
getHeaders = 	{
			'User-Agent' : user_agent

		}


session = requests.Session()
###########################################################################
#add system CAs for cert checking

#if you get some SSL errors, it's likely you have issues with Certificate Authority file.
#To fix this usually you need to provide a proper CA file to this program.
#If you're on LINUX, your system usually has actual file - just google its location
#and set the REQUESTS_CA_BUNDLE env variable in the next line:

if platform == "linux":
	print("OS: Linux; changing certs environment variable...")
	os.environ['REQUESTS_CA_BUNDLE'] = os.path.join('/etc/ssl/certs', 'ca-certificates.crt')
	print("Certs env variable changed: REQUESTS_CA_BUNDLE={0}".format(os.getenv('REQUESTS_CA_BUNDLE')))

#if you're on WINDOWS, it probably should work for you. Extracting
if platform == "win32":
	import wincertstore
	print("OS: Windows; extracting SSL certificates")
	file = open('./certs_extracted', 'w')
	for storename in ["CA", "ROOT"]:
		with wincertstore.CertSystemStore(storename) as store:
			for cert in store.itercerts(usage=wincertstore.SERVER_AUTH):
				pem = cert.get_pem()
				file.write(pem + '\n')
	file.close()
	os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'certs_extracted')
	print("Certificates extracted. Certs env variable changed: REQUESTS_CA_BUNDLE={0}".format(os.getenv('REQUESTS_CA_BUNDLE')))

###################################################################################
email = input("email: ")
password = getpass.getpass('password: ')

######################################################################################
#logging in from mobile version of VK (it's cleaner)
loginUrl = 'https://m.vk.com'
loginHTML = session.get(loginUrl)
print('Getting HTML of m.vk.com login page... ', loginHTML)

loginFormAction = getFormAction(loginHTML.text)
if not loginFormAction:
	if platform == "win32":
		os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
	raise Exception('Login link is not found, probably vk changed login flow')

loginFormData = 	{
				'email' : email,
				'pass' : password
			}

loginResponse = session.post(loginFormAction, loginFormData)
print('Trying to log in... ', loginResponse)
########################################################################################

match = re.search('authcheck', loginResponse.text)
if match:
	print('Two-factor authentication is enabled.')

	TFA_url = 'https://m.vk.com' + getFormAction(loginResponse.text)
	if TFA_url == 'https://m.vk.com':
		raise Exception('Failed to get 2FA url for auth request')
		if platform == "win32":
			os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
	
	#print(TFA_url)
	TFA_code = input('Enter the 2FA code from your authenticator app or VK support private message: ')
	TFAFormData = 	{
				'_ajax' : '1',
				'code' : TFA_code
			}
	TFAHeaders = 	{
				'User-Agent' : user_agent,
				'Content-Type' : 'application/x-www-form-urlencoded'
			}
	TFA_responce = session.post(TFA_url, headers=TFAHeaders, data=TFAFormData)
	print('Sending POST with 2FA... ', TFA_responce)
#######################################################################################
#vk hash and owner_id are user specific
#get vk hash (is not used now, probably will be used later)
rs = session.get('https://vk.com', headers=getHeaders)
match = re.search(r'(hash)=([a-zA-Z0-9]*)', rs.text)
if match is None:
	if platform == "win32":
		os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
	raise Exception('Failed to get vk hash: bad login or vk html markup was changed')
vk_hash = match.group(2)
print('HASH is: ' + vk_hash)

#########################
#f=open('./tmp', 'w')
#f.write(rs.text)
#f.close()
#########################


#get user id
match = re.search(r'\"id\":([0-9]{1,9}),', rs.text)
if match is None:
	if platform == "win32":
		os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
	raise Exception('Failed to get user id, probably vk html markup changed')
owner_id = match.group(1)
print('User id: ' + owner_id)

###################################################################################33
f = open('./dump', 'w', encoding='utf-8')
f.close()
f = open('./dump', 'a', encoding='utf-8')

offset = 0
trackCounter = 0
headers = 	{
			'User-Agent' : user_agent,
			'Content-Type' : 'application/x-www-form-urlencoded',
			'X-Requested-With' : 'XMLHttpRequest'
		}
data = 	{
		'act' : 'load_section',
		'al' : '1',
		'claim' : '0',
		'offset' : str(offset),
		'playlist_id' : '-1',
		'type' : 'playlist',
		'owner_id' : owner_id
	}

while offset < maxAudioNumber:

	data['offset']= str(offset)

	rs = session.post(urlAudioPHP, headers=headers, data=data)
	print('Sending POST to al_audio.php... ', rs, 'CURRENT OFFSET=', offset)

	raw_response = rs.text
	match = re.search(r'\{(.*)\}', raw_response)
	cleanJSON = match.group(0)

	#f = open('./json_response', 'w')
	#f.write(cleanJSON)

	parsedJSON = json.loads(cleanJSON)
	
	trackCounter += len(parsedJSON['list'])

	for i in range(len(parsedJSON['list'])):
		f.write(html.unescape(parsedJSON['list'][i][4]) + ' - ' +  html.unescape(parsedJSON['list'][i][3]) + '\n')
	
	offset += len(parsedJSON['list'])

f.close()

print('Tracks written to ./dump: ', trackCounter)
if platform == "win32":
	os.remove(os.getenv('REQUESTS_CA_BUNDLE'))
