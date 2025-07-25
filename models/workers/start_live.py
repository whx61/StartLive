# package import
from PySide6.QtCore import Slot

# local package import
import config
import constant
from exceptions import StartLiveError
from models.log import get_logger
from models.workers.base import BaseWorker, run_wrapper
from sign import livehime_sign, order_payload


class StartLiveWorker(BaseWorker):
    def __init__(self, area):
        super().__init__(name="开播任务")
        self.area = area

    @Slot()
    @run_wrapper
    def run(self, /) -> None:
        self.start_live(self.area)

    @classmethod
    def start_live(cls, area):
        logger = get_logger(cls.__name__)
        live_url = "https://api.live.bilibili.com/room/v1/Room/startLive"
        # self.fetch_upstream()
        if constant.START_LIVE_AUTH_CSRF:
            logger.info("startLive sign with csrf")
            live_data = livehime_sign({
                "area_v2": area,
                "csrf_token": config.cookies_dict["bili_jct"],
                "csrf": config.cookies_dict["bili_jct"],
                "room_id": config.room_info["room_id"],
                "type": 2,
            })
        else:
            logger.info("startLive sign without csrf")
            live_data = livehime_sign({
                "room_id": config.room_info["room_id"],
                "area_v2": area,
                "type": 2,
            })
            live_data.update({
                "csrf_token": config.cookies_dict["bili_jct"],
                "csrf": config.cookies_dict["bili_jct"]
            })
            live_data = order_payload(live_data)
        logger.info(f"startLive Request")
        response = config.session.post(live_url, data=live_data)
        response.encoding = "utf-8"
        logger.info("startLive Response")
        response = response.json()
        match response["code"]:
            case 0:
                config.stream_status.update({
                    "stream_addr": response["data"]["rtmp"]["addr"],
                    "stream_key": response["data"]["rtmp"]["code"]
                })
            case 60024:
                logger.warning(f"startLive Response face auth: {response}")
                config.stream_status.update({
                    "required_face": True,
                    "face_url": response["data"]["qr"]
                })
            case _:
                logger.error(f"startLive Response error: {response}")
                raise StartLiveError(response["message"])

    @staticmethod
    def fetch_upstream():
        raise DeprecationWarning("fetch_upstream is deprecated")
        stream_url = "https://api.live.bilibili.com/xlive/app-blink/v1/live/FetchWebUpStreamAddr"
        stream_data = livehime_sign({
            "backup_stream": 0,
        })
        stream_data.update({
            "csrf_token": config.cookies_dict["bili_jct"],
            "csrf": config.cookies_dict["bili_jct"]
        })
        stream_data = order_payload(stream_data)
        response = config.session.post(stream_url, data=stream_data)
        response.encoding = "utf-8"
        response = response.json()
        return response["data"]["addr"]["addr"], response["data"]["addr"][
            "code"]

    @staticmethod
    def on_exception(parent_window: "StreamConfigPanel", *args, **kwargs):
        parent_window.start_btn.setEnabled(True)
        parent_window.stop_btn.setEnabled(False)
        # parent_window.parent_combo.setEnabled(True)
        # parent_window.child_combo.setEnabled(True)
        parent_window.save_area_btn.setEnabled(True)
