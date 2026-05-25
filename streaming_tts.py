import os
import re
import base64
import time
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tts.v20190823 import tts_client, models


def split_text_to_sentences(text):
    text = (text or '').strip()
    if not text:
        return []

    parts = re.split(r'([。！？；\n])', text)
    sentences = []
    current = ''

    for part in parts:
        if not part:
            continue
        current += part
        if re.match(r'[。！？；\n]', part):
            sentence = current.strip()
            if sentence:
                sentences.append(sentence)
            current = ''

    if current.strip():
        sentences.append(current.strip())

    if not sentences and text:
        return [text]

    return sentences


class StreamingTTSService:
    def __init__(self, secret_id=None, secret_key=None, app_id=None):
        self.secret_id = secret_id or os.environ.get('TENCENT_SECRET_ID')
        self.secret_key = secret_key or os.environ.get('TENCENT_SECRET_KEY')
        self.appid = app_id or int(os.environ.get('TENCENT_APP_ID', '0'))

        self.voice_type = 101007
        self.speed = 1.0
        self.volume = 5
        self.codec = 'mp3'

    def _create_client(self):
        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = 'tts.tencentcloudapi.com'
        http_profile.reqTimeout = 30

        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile

        return tts_client.TtsClient(cred, '', client_profile)

    def synthesize(self, text, voice_type=None, speed=None, volume=None):
        try:
            req = models.TextToVoiceRequest()
            req.Text = text
            req.SessionId = str(int(time.time() * 1000))
            req.VoiceType = voice_type if voice_type is not None else self.voice_type
            req.Speed = speed if speed is not None else self.speed
            req.Volume = volume if volume is not None else self.volume
            req.Codec = self.codec

            client = self._create_client()
            resp = client.TextToVoice(req)

            if resp.Audio:
                audio_data = base64.b64decode(resp.Audio)
                return {
                    'success': True,
                    'audio': audio_data,
                    'request_id': resp.RequestId,
                }

            return {'success': False, 'error': 'No audio data returned'}

        except TencentCloudSDKException as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': f'TTS synthesis error: {str(e)}'}

    def synthesize_sentences_stream(self, text, voice_type=None, speed=None, volume=None):
        sentences = split_text_to_sentences(text)
        if not sentences:
            return

        for index, sentence in enumerate(sentences):
            result = self.synthesize(sentence, voice_type, speed, volume)
            if not result['success']:
                yield {
                    'success': False,
                    'index': index,
                    'text': sentence,
                    'error': result.get('error', 'TTS synthesis failed'),
                }
                return

            yield {
                'success': True,
                'index': index,
                'text': sentence,
                'audio': result['audio'],
                'audio_base64': base64.b64encode(result['audio']).decode('utf-8'),
                'request_id': result.get('request_id'),
            }

    def synthesize_streaming(self, text, voice_type=None, speed=None, volume=None):
        for item in self.synthesize_sentences_stream(text, voice_type, speed, volume):
            if item['success']:
                yield item['audio']
            else:
                yield None
                return

    def synthesize_base64_streaming(self, text, voice_type=None, speed=None, volume=None):
        for item in self.synthesize_sentences_stream(text, voice_type, speed, volume):
            if item['success']:
                yield item['audio_base64']
            else:
                yield None
                return


_streamservice_instance = None


def get_streaming_tts_service():
    global _streamservice_instance
    if _streamservice_instance is None:
        _streamservice_instance = StreamingTTSService()
    return _streamservice_instance


def synthesize_speech_stream(text, voice_type=None, speed=None, volume=None):
    tts = get_streaming_tts_service()
    return tts.synthesize(text, voice_type, speed, volume)


def synthesize_speech_stream_base64(text, voice_type=None, speed=None, volume=None):
    tts = get_streaming_tts_service()
    return tts.synthesize_base64_streaming(text, voice_type, speed, volume)


def synthesize_speech_sentences_stream(text, voice_type=None, speed=None, volume=None):
    tts = get_streaming_tts_service()
    return tts.synthesize_sentences_stream(text, voice_type, speed, volume)
