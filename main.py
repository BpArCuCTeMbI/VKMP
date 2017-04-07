import requests
import re
import json

def getFormAction(html: 'html code with login form') -> str:
	"""
	function to get the url for authorization request	
	"""
	form_action = re.findall(r'<form(?= ).* action="(.+)"', html)
	if form_action:
		return form_action[0]

def getTwoFactorAction(html: 'html code with two-factor auth form') -> str:
	"""
	function to get the url for two-factor auth request
	"""
	TFA_url = re.findall(r'<form(?= ).* action="(.+)"', html)
	if TFA_url:
		return TFA_url[0]

###########################################################################
user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'

getHeaders = 	{
			'User-Agent' : user_agent

		}


session = requests.Session()

email = input("email: ")
password = input("password: ")

######################################################################################
#logging in from mobile version of VK (it's cleaner)
loginUrl = 'https://m.vk.com'
loginHTML = session.get(loginUrl)
print('Getting HTML of m.vk.com login page... ', loginHTML)

loginFormAction = getFormAction(loginHTML.text)
if not loginFormAction:
	raise Exception('Login link is not found, probably vk changed login flow')

loginFormData = 	{
				'email' : email,
				'pass' : password
			}

loginResponse = session.post(loginFormAction, loginFormData)
print('Trying to log in... ', loginResponse)
########################################################################################

match = re.search('код подтверждения', loginResponse.text)
if match:
	print('Two-factor authentication is enabled.')

	TFA_url = 'https://m.vk.com' + getTwoFactorAction(loginResponse.text)
	if TFA_url == 'https://m.vk.com':
		raise Exception('Failed to get 2fa_url for auth request')
	
	#print(TFA_url)
	TFA_code = input('Enter the 2FA code from your authenticator app: ')
	TFAFormData = 	{
				'_ajax' : '1',
				'code' : TFA_code
			}
	TFAHeaders = 	{
				'User-Agent' : user_agent,
				'Content-Type' : 'application/x-www-form-urlencoded'
			}
	TFA_responce = session.post(TFA_url, headers=TFAHeaders, data=TFAFormData)
	print('Sending POST with TFA... ', TFA_responce)
#######################################################################################
#vk hash and owner_id are user specific
#get vk hash (is not used now, probably will be used later)
rs = session.get('https://vk.com', headers=getHeaders)
match = re.search(r'(hash)=([a-zA-Z0-9]*)', rs.text)
if match is None:
	raise Exception('Failed to get vk hash')
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
	raise Exception('Failed to get user id, probably vk html markup changed')
owner_id = match.group(1)
print('User id: ' + owner_id)

###################################################################################33
data = 	{
		'act' : 'load_silent',
		'al' : '1',
		'album_id' : '-2',
		'band' : 'false',
		'owner_id' : owner_id
	}

headers = 	{
			'User-Agent' : user_agent,
			'Content-Type' : 'application/x-www-form-urlencoded',
			'X-Requested-With' : 'XMLHttpRequest'
		}

rs = session.post('https://vk.com/al_audio.php', headers=headers, data=data)
print('Sending POST to al_audio.php... ', rs)

raw_response = rs.text
match = re.search(r'\{(.*)\}', raw_response)
cleanJSON = match.group(0)

#f = open('./json_response', 'w')
#f.write(cleanJSON)

parsedJSON = json.loads(cleanJSON)

f = open('./dump', 'w')

trackCounter = 0
for i in range(len(parsedJSON['list'])):
	f.write(parsedJSON['list'][i][4] + ' - ' +  parsedJSON['list'][i][3] + '\n')
	trackCounter++
print('Tracks written to ./dump: ' + trackCounter)
