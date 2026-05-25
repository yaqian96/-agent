import os
import json
import base64
import hashlib
import time
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tts.v20190823 import tts_client, models

class TTSService:
    def __init__(self, secret_id=None, secret_key=None, app_id=None):
        self.secret_id = secret_id or os.environ.get('TENCENT_SECRET_ID')
        self.secret_key = secret_key or os.environ.get('TENCENT_SECRET_KEY')
        self.app_id = app_id or int(os.environ.get('TENCENT_APP_ID', '0'))
        
        self.voice_type = 101007
        self.speed = 1.0
        self.volume = 5
        self.codec = 'mp3'
        
    def _create_client(self):
        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "tts.tencentcloudapi.com"
        
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        
        client = tts_client.TtsClient(cred, "", client_profile)
        return client
    
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
                    'request_id': resp.RequestId
                }
            else:
                return {
                    'success': False,
                    'error': 'No audio data returned'
                }
                
        except TencentCloudSDKException as e:
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'TTS synthesis error: {str(e)}'
            }
    
    def synthesize_to_file(self, text, output_path, voice_type=None, speed=None, volume=None):
        result = self.synthesize(text, voice_type, speed, volume)
        
        if result['success']:
            with open(output_path, 'wb') as f:
                f.write(result['audio'])
            return {
                'success': True,
                'path': output_path,
                'request_id': result['request_id']
            }
        return result
    
    def get_voice_type_name(self, voice_type=None):
        voice_types = {
            0: '智逍遥',
            1: '智萌小姐姐',
            5: '智云',
            6: '智渊',
            7: '智甜',
            1001: '云andy',
            1002: '云xiaoning',
            1003: '云xiaobai',
            1004: '云xiaoxiao',
            1005: '云xiaoyi',
            1006: '云xiaokun',
            1007: '云xiaoni',
            1008: '云xiaoyun',
            1009: '云xiaoming',
            1010: '云xiaoyu',
            1011: '云xiaomei',
            1012: '云xiaowang',
            1013: '云xiaolin',
            1014: '云laoxia',
            1015: '云xiaoshuang',
            1016: '云austin',
            1017: '云jenny',
            1018: '云jeremy',
            1019: '云ella',
            1020: '云camille',
            1021: '云emily',
            1022: '云jiajia',
            1023: '云jonny',
            1024: '云xiaomeng',
            1025: '云xiaoxuan',
            1026: '云xiaoyan',
            1027: '云annie',
            1028: '云bruce',
            1029: '云alison',
            1030: '云bella',
            1031: '云alice',
            1032: '云nova',
            1033: '云arictar',
            1034: '云chuangjiang',
            1035: '云he',
            1036: '云tianmei',
            1037: '云yue',
            101007: '云小梦(推荐)',
            101008: '云小月(推荐)',
            101009: '云贝贝(推荐)',
            101010: '云媛珍(推荐)',
        }
        
        vt = voice_type if voice_type is not None else self.voice_type
        return voice_types.get(vt, f'Voice-{vt}')

_tts_service_instance = None

def get_tts_service():
    global _tts_service_instance
    if _tts_service_instance is None:
        _tts_service_instance = TTSService()
    return _tts_service_instance

def synthesize_speech(text, voice_type=None, speed=None, volume=None):
    tts = get_tts_service()
    return tts.synthesize(text, voice_type, speed, volume)

def get_voice_types():
    tts = get_tts_service()
    return {
        'current': tts.voice_type,
        'types': {
            0: '智逍遥',
            1: '智萌小姐姐',
            101007: '云小梦(推荐女声)',
            101008: '云小月(推荐女声)',
            101009: '云贝贝(推荐女声)',
            101010: '云媛珍(推荐女声)',
            6: '智渊(男声)',
            5: '智云(女声)',
            7: '智甜(女声)',
        }
    }
