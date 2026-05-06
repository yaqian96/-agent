# 🌤️ 智能天气穿搭助手

一个基于 Python 的智能天气穿搭助手 Agent，支持天气查询、穿搭建议、旅游规划、费用估算等功能，并接入了智谱清言 LLM 实现智能对话交互。

## ✨ 功能特性

### 🌡️ 天气查询
- 自动定位当前城市
- 支持全国主要城市天气查询
- 未来一周天气预报
- 温度变化趋势可视化

### 👔 穿搭建议
- 根据温度、湿度、风力智能推荐穿搭
- 上衣、下装、鞋子、配饰全方位建议
- 紫外线防护提醒
- 雨天带伞提示

### 🗺️ 旅游规划
- 智能推荐景点（支持文化、户外、亲子、美食等类型）
- 根据天气推荐合适的游玩路线
- 支持高级旅游规划（人数、预算、出发地、游玩天数、游玩风格、美食偏好）
- 最多生成 3 条旅游方案，最少 1 条
- 考虑儿童门票优惠

### 💰 费用估算
- 门票费用计算
- 住宿费用估算
- 餐饮费用估算
- 当地交通费用估算
- 往返交通费用估算

### 🤖 智能对话
- 接入智谱清言 GLM-4-Flash 模型
- 自然语言对话交互
- 图文结合的结果展示
- 支持天气、穿搭、旅游、费用等多场景问答

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 无需额外数据库

### 安装依赖

```bash
cd weather_outfit_agent
pip install -r requirements.txt
```

### 启动服务

```bash
python web_server.py
```

服务启动后，访问 http://localhost:5000 即可使用。

## 📁 项目结构

```
weather_outfit_agent/
├── web_server.py          # Web 服务器主程序
├── weather_api.py         # 天气 API 接口
├── analyzer.py            # 天气数据分析
├── outfit_recommender.py  # 穿搭推荐算法
├── visualizer.py          # 图表可视化
├── config.py              # 配置文件
├── requirements.txt       # Python 依赖
├── templates/
│   └── index.html         # 前端页面
├── charts/                # 天气图表缓存
├── render.yaml            # Render 部署配置
└── Procfile               # 进程启动配置
```

## 🌐 在线部署

### Render 免费部署

1. 将代码推送到 GitHub
2. 在 [Render](https://render.com) 创建 Web Service
3. 连接你的 GitHub 仓库
4. 配置环境变量 `ZHIPU_API_KEY`
5. 选择 Free 计划即可部署

详细部署步骤请参考项目中的 `render.yaml` 配置文件。

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ZHIPU_API_KEY` | 智谱清言 API Key | 内置默认值 |
| `PORT` | 服务端口 | `5000` |

## 📊 技术栈

- **后端**: Python 3, HTTP Server
- **前端**: HTML5, CSS3, JavaScript
- **天气数据**: Open-Meteo API（免费无需 Key）
- **定位服务**: 多源 IP 定位服务
- **AI 对话**: 智谱清言 GLM-4-Flash
- **图表**: 动态生成天气趋势图

## 🎯 使用示例

### 天气查询
输入城市名称，如 `成都`、`北京`、`上海`

### 穿搭建议
- `今天适合穿什么？`
- `明天天气怎么样？`
- `未来一周天气趋势`

### 旅游规划
- `成都旅游攻略`
- `上海旅游推荐`
- `4个大人2个小孩预算8000去上海玩3天，喜欢美食`

### 费用估算
- `去北京旅游大概花多少钱？`
- `成都旅游费用预算`

## 📝 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 主页 |
| `/api/locate` | GET | 自动定位当前城市 |
| `/api/weather?city=成都` | GET | 获取指定城市天气 |
| `/api/chat` | POST | 发送对话消息 |

## ⚠️ 注意事项

- 天气数据来源于 Open-Meteo，免费且无需 API Key
- 智谱清言 LLM 需要有效的 API Key
- 免费部署方案（Render Free）有 15 分钟空闲休眠限制

## 📄 License

MIT License

---

Made with ❤️ for smart weather outfit recommendations
