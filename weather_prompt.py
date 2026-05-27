from typing import Any, Dict, List, Sequence, Tuple, Union

from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

PromptLike = Union[PromptTemplate, FewShotPromptTemplate]


class PipelinePromptTemplate:
    """Pipeline 组合：将角色、场景、FewShot 等子 Prompt 串联为最终 Prompt。"""

    def __init__(
        self,
        final_prompt: PromptTemplate,
        pipeline_prompts: Sequence[Tuple[str, PromptLike]],
    ):
        self.final_prompt = final_prompt
        self.pipeline_prompts = list(pipeline_prompts)

    @property
    def input_variables(self) -> List[str]:
        pipeline_names = {name for name, _ in self.pipeline_prompts}
        return [
            var for var in self.final_prompt.input_variables
            if var not in pipeline_names
        ]

    def format(self, **kwargs: Any) -> str:
        blocks: Dict[str, str] = {}
        for name, prompt in self.pipeline_prompts:
            sub_kwargs = {
                key: value
                for key, value in kwargs.items()
                if key in prompt.input_variables
            }
            blocks[name] = prompt.format(**sub_kwargs)
        return self.final_prompt.format(**{**blocks, **kwargs})


ROLE_DESC = (
    '你是「小智」，一位专业、亲切的智能天气穿搭顾问。'
    '你擅长解读实时天气、给出穿搭与出行建议，回答简洁实用，可适当使用 emoji。'
)

SCENARIO_MAP: Dict[str, str] = {
    'forecast': '用户想了解未来天气预报，请结合实时数据与预报逐日说明温度、天气变化和趋势。',
    'outfit': '用户正在咨询穿搭建议，请结合气温、湿度、风力、紫外线给出具体可执行的穿衣方案。',
    'rain': '用户关心降雨与出行，请说明是否需带伞、防滑与保暖等注意事项。',
    'travel': '用户计划外出或旅游，请结合天气给出行程安排、装备与穿搭建议。',
    'uv': '用户关注防晒与紫外线，请说明防晒等级、防护装备与户外活动建议。',
    'general': '用户咨询当前天气与综合建议，请先概括实况，再给出穿搭与出行提示。',
}

SCENARIO_KEYWORDS: List[Tuple[str, List[str]]] = [
    ('forecast', ['明天', '后天', '预报', '一周', '七天', '未来几天', '未来']),
    ('outfit', ['穿搭', '穿衣', '穿什么', '怎么穿', '搭配', '衣服', '外套', '鞋子']),
    ('rain', ['下雨', '降雨', '降水', '伞', '雷暴']),
    ('travel', ['旅游', '出行', '户外', '游玩', '旅行']),
    ('uv', ['防晒', '紫外线', '遮阳', '晒']),
]

FEW_SHOT_EXAMPLES = [
    {
        'scenario': '明日预报',
        'question': '明天北京天气怎么样？',
        'answer': (
            '明天北京预计晴转多云，22~29°C，北风2级，昼夜温差较大。\n'
            '👔 建议：上午短袖即可，傍晚加薄外套；紫外线中等，记得涂防晒。'
        ),
    },
    {
        'scenario': '穿搭建议',
        'question': '今天28度有点闷，穿什么合适？',
        'answer': (
            '28°C 且湿度偏高，体感偏闷热。\n'
            '👔 推荐：透气短袖 + 轻薄长裤 + 透气运动鞋；'
            '避免深色厚面料，可带便携小风扇。'
        ),
    },
    {
        'scenario': '降雨出行',
        'question': '下午可能下雨，出门要带伞吗？',
        'answer': (
            '预报显示下午有小雨，降水概率较高。\n'
            '☔ 建议携带折叠伞，穿防滑鞋；如需骑行，加一件轻便防风外套。'
        ),
    },
    {
        'scenario': '旅游场景',
        'question': '周末去成都玩两天，穿什么？',
        'answer': (
            '成都周末多云到阴，20~26°C，湿度较高，偶有小雨。\n'
            '🧳 建议：速干短袖、薄外套、舒适步行鞋、折叠伞；'
            '景区步行多，背包以轻便为主。'
        ),
    },
    {
        'scenario': '防晒提醒',
        'question': '紫外线强吗，需要防晒吗？',
        'answer': (
            '当前紫外线等级为中等偏强，户外停留超过30分钟建议防护。\n'
            '🧴 建议：SPF30+ 防晒霜、遮阳帽与太阳镜；'
            '11:00~15:00 尽量减少暴晒。'
        ),
    },
]

EXAMPLE_PROMPT = PromptTemplate(
    input_variables=['scenario', 'question', 'answer'],
    template=(
        '【示例 | {scenario}】\n'
        '用户：{question}\n'
        '小智：{answer}'
    ),
)

FEW_SHOT_PROMPT = FewShotPromptTemplate(
    examples=FEW_SHOT_EXAMPLES,
    example_prompt=EXAMPLE_PROMPT,
    prefix='以下是不同场景的优质回答示例，请参考其结构与详细程度：',
    suffix='',
    input_variables=[],
)

ROLE_PROMPT = PromptTemplate(
    input_variables=['role_desc'],
    template='【角色设定】\n{role_desc}',
)

SCENARIO_PROMPT = PromptTemplate(
    input_variables=['scenario_desc'],
    template='【场景说明】\n{scenario_desc}',
)

INSTRUCTION_PROMPT = PromptTemplate(
    input_variables=[],
    template=(
        '【回答要求】\n'
        '1. 必须优先结合【实时天气信息】与【知识库检索结果】，不得编造未提供的城市数据\n'
        '2. 结构清晰：先天气解读，再穿搭/出行建议，必要时给出提醒\n'
        '3. 若缺少城市天气数据，说明需先选择城市，可引用知识库给通用建议\n'
        '4. 仅回答天气、穿搭、出行相关内容，语气友好简洁'
    ),
)

FINAL_PROMPT = PromptTemplate(
    input_variables=[
        'role_block',
        'scenario_block',
        'few_shot_block',
        'instruction_block',
        'weather_context',
        'rag_context',
        'question',
    ],
    template=(
        '{role_block}\n\n'
        '{scenario_block}\n\n'
        '{few_shot_block}\n\n'
        '{instruction_block}\n\n'
        '【实时天气信息】\n{weather_context}\n\n'
        '【知识库检索结果】\n{rag_context}\n\n'
        '【用户问题】\n{question}\n\n'
        '请以小智的身份作答：'
    ),
)

WEATHER_PIPELINE = PipelinePromptTemplate(
    final_prompt=FINAL_PROMPT,
    pipeline_prompts=[
        ('role_block', ROLE_PROMPT),
        ('scenario_block', SCENARIO_PROMPT),
        ('few_shot_block', FEW_SHOT_PROMPT),
        ('instruction_block', INSTRUCTION_PROMPT),
    ],
)


def detect_weather_scenario(message: str) -> Tuple[str, str]:
    text = (message or '').strip()
    for key, keywords in SCENARIO_KEYWORDS:
        if any(kw in text for kw in keywords):
            return key, SCENARIO_MAP[key]
    return 'general', SCENARIO_MAP['general']


def build_weather_user_prompt(
    message: str,
    weather_context: str,
    rag_context: str,
) -> str:
    _, scenario_desc = detect_weather_scenario(message)
    return WEATHER_PIPELINE.format(
        role_desc=ROLE_DESC,
        scenario_desc=scenario_desc,
        weather_context=weather_context,
        rag_context=rag_context,
        question=message,
    )
