import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import logging

# 로그 설정
logging.basicConfig(
    filename="bot_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNELS = {
    "channel_name_1": {
        "channel_id": os.getenv("CHANNEL_1_ID"),
        "webhook_url": os.getenv("CHANNEL_1_WEBHOOK")
    },
    "channel_name_2": {
        "channel_id": os.getenv("CHANNEL_2_ID"),
        "webhook_url": os.getenv("CHANNEL_2_WEBHOOK")
    },
    "channel_name_3": {
        "channel_id": os.getenv("CHANNEL_3_ID"),
        "webhook_url": os.getenv("CHANNEL_3_WEBHOOK")
    }
}

LAST_VIDEO_FILE = "last_videos.json"  # 마지막 확인된 비디오 ID 저장 파일


# 마지막 확인된 비디오 ID를 읽는 함수
def read_last_video_ids(file_path=LAST_VIDEO_FILE):
    try:
        with open(file_path, "r") as file:
            return json.load(file)  # JSON 파일 읽기
    except FileNotFoundError:
        logging.info(f"'{file_path}' 파일을 찾을 수 없습니다. 기본값으로 초기화합니다.")
        return {channel: None for channel in CHANNELS}  # 채널별 초기화


# 새로운 마지막 비디오 ID를 저장하는 함수
def save_last_video_ids(last_video_ids, file_path=LAST_VIDEO_FILE):
    try:
        with open(file_path, "w") as file:
            json.dump(last_video_ids, file, indent=4)  # JSON 형식으로 저장
    except Exception as e:
        logging.error(f"비디오 ID 저장 실패: {str(e)}")


# YouTube API를 통해 채널의 최신 비디오 정보 가져오기
def get_latest_video(channel_id):
    api_url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}" \
              f"&channelId={channel_id}&part=snippet&order=date&maxResults=1"
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            if data["items"]:
                video_id = data["items"][0]["id"].get("videoId")  # 비디오 ID
                title = data["items"][0]["snippet"]["title"]  # 비디오 제목
                return {"video_id": video_id, "title": title}
            else:
                logging.info(f"채널 ID {channel_id}: 새 동영상이 없습니다.")
        elif response.status_code == 403:
            logging.warning(f"API 쿼터 초과 - 채널 ID: {channel_id}")
        else:
            logging.error(f"API 호출 실패 - 상태 코드: {response.status_code}, 응답: {response.text}")
    except Exception as e:
        logging.error(f"API 요청 실패: {str(e)}")
    return None


# 디스코드로 메시지 보내기
def send_discord_message(channel_name, webhook_url, video):
    message = {
        "content": f"https://www.youtube.com/watch?v={video['video_id']}"
    }
    try:
        response = requests.post(webhook_url, json=message)
        if response.status_code == 204:
            logging.info(f"{channel_name} 채널: 알림이 성공적으로 전송되었습니다.")
        else:
            logging.error(f"{channel_name} 채널: 알림 전송 실패 - 상태 코드: {response.status_code}, 응답: {response.text}")
    except Exception as e:
        logging.error(f"{channel_name} 채널: 알림 전송 중 오류 발생: {str(e)}")


# 주기적으로 확인하는 메인 실행 함수
def main():
    logging.info("유튜브 채널 모니터링을 시작합니다...")

    # 마지막 확인된 비디오 ID 읽기
    last_video_ids = read_last_video_ids()

    while True:
        try:
            for channel_name, info in CHANNELS.items():
                latest_video = get_latest_video(info["channel_id"])  # 채널의 최신 비디오 확인

                if latest_video:
                    last_video_id = last_video_ids.get(channel_name)

                    # 새로운 동영상이 올라오면
                    if latest_video["video_id"] != last_video_id:
                        logging.info(f"{channel_name} 채널에서 새로운 영상 감지: {latest_video['title']}")
                        send_discord_message(channel_name, info["webhook_url"], latest_video)
                        last_video_ids[channel_name] = latest_video["video_id"]  # 새 비디오 ID 저장
                    else:
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        logging.info(f"{channel_name} 채널에 새로운 영상이 없습니다. ({current_time})")
                else:
                    logging.info(f"{channel_name} 채널의 최신 동영상 정보를 가져올 수 없었습니다.")

            # 마지막 확인된 비디오 ID 업데이트 저장
            save_last_video_ids(last_video_ids)

            # 10분 대기 후 다시 확인
            time.sleep(600)

        except Exception as e:
            logging.error(f"전역 오류 발생: {str(e)}")
            time.sleep(60)  # 60초 대기 후 재시작


if __name__ == "__main__":
    main()
