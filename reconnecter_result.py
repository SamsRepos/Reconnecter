from datetime import datetime

class reconnecter_result:
    def __init__(self, connected, online, current_net_id):
        self.datetime       = datetime.now()
        self.connected      = connected
        self.online         = online
        self.current_net_id = current_net_id
    