from requests import session
from datetime import datetime
import os

version = '1.2'
debug = not True

requests = session()
requests.headers.update({
    'user-agent': f'FurryApp/170  BarqCLI/{version}',
    'Content-Type': 'application/json'
})

GRAPHQL_URL = 'https://api.barq.app/graphql'
chats, max_display_name_length = {}, 0
status, channel = 'menu', 'unread'

#region Log in
def codeToHeader(email:str, code:str):
    '''Converts a code to an auth header'''
    temp = requests.post('https://api.barq.app/account-provider/email/login', json={'email':email,'code': code}).text.replace('"', '')
    if 'CODE_INVALID' in temp: temp = ''
    return temp

auth = open('auth.txt').read() if os.path.isfile('auth.txt') else ''
had_auth = auth != ''

while auth == '':
    print('How would you like to login?')
    print('Send code to email (e)')
    print('Auth header (a)')

    inCode = input('> ').lower()
    if inCode == 'e':
        os.system('cls')
        email = input('Enter email to send login code to.\n>')
        temp = requests.post('https://api.barq.app/account-provider/email/request-code', json={'email':email}).text
        os.system('cls')
        print(f'{temp}\n')
        print('Please check your email for a login code and put it below\n')
        code = input('Enter code\n> ')
        auth = codeToHeader(email,code)
        print(auth)

    elif inCode == 'a':
        os.system('cls')
        auth = input('Enter Auth header\n> ')

requests.headers.update({'Authorization': f'Bearer {auth}'})
if not had_auth: open('auth.txt','w').write(auth)
#endregion

class functions:
    def relativeTime(date_string):
        '''Takes the date and makes it relative

        Args:
            date_string (str): the date string (Ex: 2024-01-30T02:38:45Z)

        Returns:
            str: relative time (Ex: 14 hours ago)
        '''
        # Convert the input string to a datetime object
        # sourcery skip: instance-method-first-arg-name
        date_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

        current_time = datetime.utcnow() # Current time+Date

        # Calculate the time difference
        timeDiff = current_time - date_object

        # Get the number of weeks, days, hours, and minutes
        weeks, days = divmod(timeDiff.days, 7)
        hours, remainder = divmod(timeDiff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        # Generate the relative time string
        if weeks > 0:
            return f"{weeks} {'week' if weeks == 1 else 'weeks'} ago"
        elif days > 0:
            return f"{days} {'day' if days == 1 else 'days'} ago"
        elif hours > 0:
            return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
        else:
            return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"

class requestData:
    markOnline = r'''''' # TODO: Grab json
    likeInfo = r'''{"operationName":null,"variables":{"limit":9,"offset":0},"query":"query LikesOverview($limit: Int!, $offset: Int!) {\n    user {\n      profileRelations(limit: $limit, offset: $offset, type: [$TYPE$]) {\n      ...ProfileRelation\n    }\n  }\n}\n\nfragment ProfileRelation on ProfileRelation {\n  profile {\n    ...OverviewProfile\n  }\n  updatedAt\n}\n\nfragment OverviewProfile on Profile {\n  ...MinimalProfile\n}\n\nfragment MinimalProfile on Profile {\n  uuid\n  displayName\n  shareHash\n  id\n}"}'''
    getChats = r'''{"operationName":"ChatsOverview","variables":{},"query":"query ChatsOverview {\n  chats {\n    id\n    participants {\n      profile {\n        displayName\n      \n      shareHash}\n    }\n    lastMessage {\ncontent\n    }\n    unreadMessageCount\n  }\n}"}'''
    readChat = r'''{"operationName":"ChatDetails","variables":{"id":"$IDHERE$"},"query":"query ChatDetails($id: Int!) {\n      chat(id: $id) {\n    id\n    participants {\n          profile {\n            id\n        uuid\n        displayName\n        shareHash\n      }\n    }\n    messages {\n          id\n      profile {\n            id\n      }\n      createdAt\n      content\n    }\n  }\n}"}'''
    markAsRead = r'''{"operationName":"ChatMarkRead","variables":{"id":"$IDHERE$","from":"$TIMEHERE$"},"query":"mutation ChatMarkRead($id: Int!, $from: DateTime!) {\n  chatMarkRead(id: $id, from: $from)\n}"}'''
    sendMessage = r'''{"operationName":"sendChatMessage","variables":{"id":"$IDHERE$","message":{"content":"MSGHERE"}},"query":"mutation sendChatMessage($id: Int!, $message: ChatMessageInput!) {\n  sendChatMessage(id: $id, message: $message) {\n    id\n    profile {\n      id\n      __typename\n    }\n    createdAt\n    content\n    __typename\n  }\n}"}'''
    createPrivateChat = r'''{"operationName":"createPrivateChat","variables":{"uuid":"$UUID$"},"query":"mutation createPrivateChat($uuid: String!) {\n    createPrivateChat(uuid: $uuid) {\n        id\n    }\n}"}'''

class requesting:
    def updateChats():
        global chats,max_display_name_length
        chats = requests.post(GRAPHQL_URL, requestData.getChats).json()['data']['chats']
        if 'u' in channel: chats = [chat for chat in chats if chat['unreadMessageCount'] >= 1]
        max_display_name_length = (
            max(
                len(participant['profile']['displayName'])
                for chat in chats[:9]
                for participant in chat['participants']
            )
            if chats
            else 0
        )

    def getLikeData(lookupType='likedBy'):
        # sourcery skip: instance-method-first-arg-name
        if lookupType not in ['likeBy','liked','mutual']: lookupType = 'likedBy' # make sure it's only an allowed type
        postData = requestData.likeInfo.replace('$TYPE$',str(lookupType))
        try:
            likes = requests.post(GRAPHQL_URL, postData).json()['data']['user']['profileRelations']
        except Exception:
            likes = []
        # print(likes)
        for person in likes:
            uuid = person['profile']['uuid'] # User ID used for a lot
            displayName = person['profile']['displayName'] # User name
            shareHash = person['profile']['shareHash'] # Used for the barq short links
            updatedAt = person['updatedAt'] # When updated - normally when liked by either user or the other person
            print(displayName,f'https://barq.app/p/{shareHash}',uuid,functions.relativeTime(updatedAt))
        print('\nPress enter to go back')

    def getChatId(uuid:str):
        # sourcery skip: instance-method-first-arg-name
        try: # Can't be asked to add fall backs rn
            chatID = requests.post(
                GRAPHQL_URL, requestData.createPrivateChat.replace('$UUID$', uuid)
            ).json()
            print(chatID)
            return chatID['data']['createPrivateChat']['id']
        except Exception as e:
            print(e)
            return 'FAIL'

    def readChat(id:int):
        # sourcery skip: instance-method-first-arg-name
        data = requestData.readChat.replace('"$IDHERE$"',str(id))
        chat_data = requests.post(GRAPHQL_URL, data).json()
        if debug: print('sent data:',data);print();print('return data:',chat_data)

        participants = chat_data['data']['chat']['participants']
        participant_dict = {
            participant['profile']['id']: participant['profile']['displayName']
            for participant in participants
        }
        messages = chat_data['data']['chat']['messages']
        print(f'https://barq.app/p/{participants[1]["profile"]["shareHash"]}')
        print(f'https://web.barq.app/profiles/{participants[1]["profile"]["uuid"]}/')
        #print(f'barq://profiles/{participants[1]["profile"]["uuid"]}/')
        print()
        print()
        for message in reversed(messages):
                sender = participant_dict[message['profile']['id']]
                print(f'{sender}: {message["content"]}')
    
    def markAsRead(chatId:int):
        # sourcery skip: instance-method-first-arg-name
        current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        data = requestData.markAsRead.replace('"$IDHERE$"',str(chatId)).replace('$TIMEHERE$',str(current_time))
        requests.post(GRAPHQL_URL, data).json()
    
    def sendMessage(id:int,msg:str):
        # sourcery skip: instance-method-first-arg-name
        data = requestData.sendMessage.replace('"$IDHERE$"', str(id)).replace(
            'MSGHERE', msg
        )
        requests.post(GRAPHQL_URL, data).json()
        requesting.markAsRead(id)
    
    def auth(auth_code:str):
        # sourcery skip: instance-method-first-arg-name
        requests.post(f'https://api.barq.app/openid-auth/{auth_code}/approve', {})

class commands:
    '''
        Do to the janky way I have coded this (for the time)
        every command comes with the args after the cmd and the current ChatID
    '''
    # TODO: make a better command system
    def checkCommand(uinput,chatId=0):
        '''Shotty command system made by GPT ngl'''
        # sourcery skip: instance-method-first-arg-name
        os.system('cls')
        
        parts = uinput.split(' ')
        cmd = parts[0][1:]
        args = parts[1:]
        cmd_func = getattr(commands, f'{cmd}CMD', None) # appending the 'CMD' to all cmds to prevent use of python funcs
        if callable(cmd_func):
            cmd_func(args,chatId)
        else: 
            input('Command not found')

    def helpCMD(args,chatId:int):
        '''Prints all commands'''
        # sourcery skip: instance-method-first-arg-name
        commandList = {
            'help': 'prints this',
            'back': 'goes back in chats',
            'read': 'marks chat as read',
            'exit': 'closes program'
        }
        for cmd, about in commandList.items():
            print(f'/{cmd} {about}')
        input("Press enter to go back")

    def backCMD(args,chatId:int):
        '''Goes back to the main menu'''
        # sourcery skip: class-extract-method, instance-method-first-arg-name
        print('Updating chats please wait')
        requesting.updateChats()
        global status
        status = 'menu'

    def bCMD(args,chatId:int):
        '''Alias of the back command'''
        # sourcery skip: instance-method-first-arg-name
        commands.backCMD(args,chatId)

    def exitCMD(args=0,chatId:int=0):
        '''Exit the program cmd'''
        # sourcery skip: instance-method-first-arg-name
        exit()

    def readCMD(args,chatId:int):
        '''Marks the chat as read'''
        # sourcery skip: instance-method-first-arg-name
        requesting.markAsRead(chatId)
        print('Updating chats please wait')
        requesting.updateChats()
        global status
        status = 'menu'

    def likesCMD(args,chatId:int=0):
        # sourcery skip: instance-method-first-arg-name
        lookUpTypes = ['likeBy','liked','mutual']
        for type in lookUpTypes:
            i = lookUpTypes.index(type)
            print(f'{i+1} | {type}')

        index = input('> ')
        lookUp = ''
        for v in list(index):
            v=int(v)
            if v > len(lookUpTypes) or v < 1: continue
            lookUp += f'{lookUpTypes[v - 1]},'

        requesting.getLikeData(lookUp[:-1])
        input()

    def chatCMD(args,chatId:int):
        # sourcery skip: instance-method-first-arg-name
        uuid = input('Please give the UUID: ') if len(args) == 0 else args[0]
        chatId = requesting.getChatId(uuid)
        if chatId == 'FAIL': input("Failed to get chatID, Please make sure you are giving a UUID\nPress enter to go back"); return''
        global status
        status = f'chat {chatId}'

    def authCMD(args,chatId:int):
        print(args,len(args))
        code = input('Please give the code: ') if len(args) == 0 else args[0]
        code = code.replace('barq-auth;', '')

        requesting.auth(code)

requesting.updateChats() # Load the chat for loop
while True:
    # Main loop with a try statement so you can Ctrl+c back to menu
    try:
        os.system('cls')
        if 'menu' in status:
            # Main Menu stuff
            if debug: print('json data:',chats)

            for chatNum, chat in enumerate(chats[:9], start=1):
                # Print all chats in the table
                participant = chat['participants'][0]
                displayName = participant['profile']['displayName']
                lastMessage = chat['lastMessage']['content']
                unreadMessageCount = chat['unreadMessageCount']
                spacing = ' '*(max_display_name_length-len(displayName))
                print(f'{chatNum} | {displayName} {spacing} ({unreadMessageCount}) | {lastMessage}')

            keys = {
                '0': 'Refresh Chats',
                'E': 'Exit',
                'R': 'Read chats',
                'U': 'Unread chats'
            }
            for i,v in keys.items():
                print(f'{i} | {v}')

            # TODO: add pages
            # print("N | Next")
            # print("P | Previous")

            uinput = input('  ∟> ').lower()
            match uinput:
                case '0':
                    # 0 = update chats
                    print('Updating chats please wait')
                    requesting.updateChats()

                case 'e' | 'q':
                    # Quits program
                    print('Bye')
                    commands.exitCMD()

                case _ if uinput.startswith('/'):
                    commands.checkCommand(uinput)

                case 'n':
                    # TODO: add pages
                    pass

                case 'p':
                    # TODO: add pages
                    pass

                case 'read' | 'unread' | 'r' | 'u':
                    channel = uinput.lower()
                    requesting.updateChats()

                case _ if uinput.isdigit() and len(chats)>=int(uinput):
                    # If its a valid number open that chat
                    chatNum = int(uinput)
                    if 1 <= chatNum <= 9:
                        print(len(chats),chatNum)
                        if debug: print('Input is valid.')
                        chatId = chats[int(chatNum)-1]['id']
                        status = f'chat {chatId}'

                case _:
                    pass

        elif 'chat' in status:
            # User chats
            chatId = int(status.split()[1])
            requesting.readChat(chatId)
            uinput = input('> ')
            if uinput.startswith('/'):
                commands.checkCommand(uinput,chatId)
            elif uinput != '' and '/python.exe' not in uinput:
                requesting.sendMessage(chatId,uinput)
        else:
            # Status broke so default to menu
            status = 'menu'
    except KeyboardInterrupt:
        if debug: exit() # Exit on Ctrl+c to allow debugging faster

        # Allows ctrl+c back to the menu
        os.system('cls')
        print('Ctrl+C (KeyboardInterrupt) detected... going home')
        status = 'menu'
        requesting.updateChats()
    except EOFError: # No fucking idea what causes it, cant be asked
        os.system('cls')
        print('Error (EOFError) detected... going home')
        status = 'menu'
        requesting.updateChats()
