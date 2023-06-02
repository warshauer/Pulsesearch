import vonage

class smsClient():
    def __init__(self, key = None, secret = None):
        if key == None:
            self._key = '6fbf02d5'
        else:
            self._key = key
        if secret == None:
            self._secret = 'e8DD6WHoQhqJkIip'
        else:
            self._secret = secret
        self._number = '18554604086'
        try:
            self._client = vonage.Client(key = self._key, secret = self._secret)
            self._sms = vonage.Sms(self._client)
        except Exception as e:
            print(e)
        
    def send(self, text, recipient):
        try:
            responseData = self._sms.send_message({"from": self._number, "to": recipient, "text": text})
            if responseData["messages"][0]["status"] == "0":
                print("Message sent successfully.")
            else:
                print(f"Message failed with error: {responseData['messages'][0]['error-text']}")
        except Exception as e:
            print(e)
