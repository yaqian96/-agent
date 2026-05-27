import os
import base64
import subprocess
import tempfile
import env_config  # noqa: F401  加载 .env
from env_config import get_int_env, tencent_config_error
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.asr.v20190614 import asr_client, models


class ASRService:
    def __init__(self, secret_id=None, secret_key=None):
        self.secret_id = secret_id or env_config.get_env('TENCENT_SECRET_ID')
        self.secret_key = secret_key or env_config.get_env('TENCENT_SECRET_KEY')
        self.appid = get_int_env('TENCENT_APP_ID', 0)

    def _create_client(self):
        if not self.secret_id or not self.secret_key:
            print('Missing TENCENT_SECRET_ID or TENCENT_SECRET_KEY')
            return None

        try:
            cred = credential.Credential(self.secret_id, self.secret_key)
            http_profile = HttpProfile()
            http_profile.endpoint = 'asr.tencentcloudapi.com'
            http_profile.reqTimeout = 30
            http_profile.postTimeout = 30

            client_profile = ClientProfile()
            client_profile.httpProfile = http_profile
            client_profile.signMethod = 'TC3-HMAC-SHA256'

            return asr_client.AsrClient(cred, 'ap-beijing', client_profile)
        except Exception as e:
            print(f'Failed to create ASR client: {e}')
            return None

    def _convert_to_pcm(self, audio_data, input_format):
        try:
            with tempfile.NamedTemporaryFile(suffix=f'.{input_format}', delete=False) as input_file:
                input_file.write(audio_data)
                input_file_path = input_file.name

            with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as output_file:
                output_file_path = output_file.name

            command = [
                'ffmpeg', '-i', input_file_path,
                '-f', 's16le', '-ar', '16000', '-ac', '1', '-y', output_file_path,
            ]

            result = subprocess.run(command, capture_output=True, text=True)
            os.unlink(input_file_path)

            if result.returncode != 0:
                print(f'FFmpeg conversion error: {result.stderr}')
                return None

            with open(output_file_path, 'rb') as f:
                pcm_data = f.read()

            os.unlink(output_file_path)
            return pcm_data

        except Exception as e:
            print(f'Conversion error: {e}')
            return None

    def _prepare_pcm_audio(self, audio_data, format='pcm'):
        actual_format = format.lower()
        if actual_format == 'pcm':
            return audio_data

        pcm_data = self._convert_to_pcm(audio_data, actual_format)
        if not pcm_data:
            raise ValueError(f'无法将 {format} 转换为 PCM，请确认已安装 ffmpeg')
        return pcm_data

    def _recognize_with_tencent(self, audio_data, format='pcm'):
        try:
            client = self._create_client()
            if not client:
                return {'success': False, 'error': tencent_config_error()}

            pcm_data = self._prepare_pcm_audio(audio_data, format)

            req = models.SentenceRecognitionRequest()
            req.ProjectId = 0
            req.SubServiceType = 2
            req.SourceType = 1
            req.VoiceFormat = 'pcm'
            req.DataLen = len(pcm_data)
            req.Data = base64.b64encode(pcm_data).decode('utf-8')
            req.EngSerViceType = '16k_zh'

            resp = client.SentenceRecognition(req)

            return {
                'success': True,
                'text': resp.Result,
                'request_id': resp.RequestId,
            }

        except ValueError as e:
            return {'success': False, 'error': str(e)}
        except TencentCloudSDKException as e:
            print(f'Tencent ASR SDK error: {e}')
            return {'success': False, 'error': f'语音识别失败: {e}'}
        except Exception as e:
            print(f'ASR recognition error: {e}')
            return {'success': False, 'error': f'语音识别失败: {str(e)}'}

    def recognize(self, audio_data, format='pcm'):
        print(f'ASR recognize called, audio length: {len(audio_data)} bytes, format: {format}')

        if len(audio_data) < 100:
            return {'success': False, 'error': '录音时间太短，请重新录制'}

        return self._recognize_with_tencent(audio_data, format)

    def recognize_file(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                audio_data = f.read()

            ext = file_path.split('.')[-1].lower()
            return self.recognize(audio_data, ext)

        except Exception as e:
            return {'success': False, 'error': f'Failed to read audio file: {str(e)}'}


_asr_service_instance = None


def get_asr_service():
    global _asr_service_instance
    if _asr_service_instance is None:
        _asr_service_instance = ASRService()
    return _asr_service_instance


def recognize_speech(audio_data, format='pcm'):
    asr = get_asr_service()
    return asr.recognize(audio_data, format)
