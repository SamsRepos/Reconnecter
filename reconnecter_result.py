from datetime import datetime

class reconnecter_result:
    def __init__(self, connected, online):
        self.datetime = datetime.now()
        self.connected = connected
        self.online    = online       
    