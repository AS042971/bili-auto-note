# Bilibili 自动打轴助手

通过本工具可以将统一的时间轴自动转换到不同的录播笔记。

首先，请确保准备好配置文件和数据文件。通过执行根目录的 `init.cmd` 或 `init.sh` 可展开示例数据。

## 生成时间轴

### 教程

1. 新建存放原始文本轴的文本文件（一般放在 `data` 目录下）
2. 修改 `config/gen_timeline.json`, 填入这些文本文件的路径和这些分p对应的偏移量，同时填入输出csv路径
3. 执行 `python gen_timeline.py` 即可生成转换的 csv 文件
4. 如果配置文件在其他位置，执行 `python gen_timeline.py <配置文件路径>`

### 配置文件示例 (json文件)

    {
        "offsets": [-585, 2344],
        "parts": ["./data/p1.txt", "./data/p2.txt"],
        "out": "./data/timeline.csv"
    }

### 配置文件说明

* `offsets`: 参考视频每个分P开始时刻对应的统一时间轴时刻，单位为秒。注意，此处的值可能为负数（比如果统一时间轴以开场对齐，但视频中包含OP时）。
* `parts`: 每个视频文本轴的路径
* `out`: 输出 csv 格式时间轴路径

### 文本轴示例

    09:45 《Next Level》
    12:04 枝江gamer们的自我介绍
    13:04 本次游戏的最大奖品竟然是她？*
    14:12 四位参赛选手的赛前采访
    15:44 分 赃 现 场*

## 输出时间轴示例 (csv文件)

    1,开场,0
    10,这是一个简单的时间轴的示例,0
    11,用于时间轴的自动化上传测试,0
    20,第一列表示时间戳对应的时刻,1
    21,单位为秒，如这行表示第21秒,0
    22,文件中的时间戳基于开场时刻,0
    23,假设这个分p 的op的长10秒,0
    24,那么第 8行则会显示为第31秒,0
    30,第二列为时间戳对应显示内容,1
    40,第三列表示它是否为重要标记,1
    41,如果填充 0表示普通时间标记,0
    42,如果填充 1表示重要时间标记,0
    43,重要标记用红色加粗形式显示,1
    50,笔记测试结束了，大家晚安啦,0
    60,回马枪,0

## 发布时间轴

### 教程

1. 确保已拥有主时间轴的 csv 文件（一般放在 `data` 目录下）
2. 修改 `config/pub_timeline.json`, 填入 cookie 和视频信息等
3. 执行 `python pub_timeline.py` 将时间轴发布至B站
4. 如果配置文件在其他位置，执行 `python pub_timeline.py <配置文件路径>`

### 获取 Cookie

* cookie 可使用 `F12` 开发人员工具从 Bilibili 网页端抓包
* 有了 cookie 能操作B站账号的大部分功能，切勿泄露或分享出去
* 请确保 cookie 中包含 `SESSDATA` 和 `bili_jct` 两项
* 为防广告，一些小号可能没有发布笔记的功能，请先在网页端进行发布笔记的测试
* 每人每天最多发布 5 篇笔记

### 配置文件示例 (json文件)

    {
        "cookie": "SESSDATA=<SESSDATA>; bili_jct=<CSRF>",
        "bvid": "BV1FQ4y1R7nv",
        "timeline": "./data/timeline.csv",
        "offsets": [-10],
        "cover": "这是一个自动发布笔记的测试\n欢迎进入笔记打轴的自动化时代",
        "publish": false
    }

### 配置文件说明

* `cookie`: 发送笔记用户的cookie，必须包含 `SESSDATA` 和 `bili_jct` 两项
* `bvid`: 目标视频BV号
* `timeline`: 时间轴文件路径
* `offsets`: 目标视频每个分P开始时刻对应的统一时间轴时刻，单位为秒。注意，此处的值可能为负数（比如果统一时间轴以开场对齐，但视频中包含OP时）。
在offsets中也可以标记`auto`或`skip`，`auto`表示自动叠加上一p的累计时长，`skip`表示跳过这一p
* `cover`: 视频转制通过时发送至评论区的文案
* `publish`: 是否自动发布
* `watch`: 是否监控视频和笔记更新。设置为`true`将自动监控视频分P和笔记文件的变化，每次目标视频分P变化或笔记文件更新时将自动更新笔记

## 小工具：监控评论区

执行 `python comment_monitor.py <目标视频BVID> <监测用户名>`即可在被监测用户发评论时收到通知

## 后续更新计划

* 实现自动监测，当视频分p数量发生变化，或本地 csv 文件变化时自动上传笔记
* 实现时间轴转换为 Potplayer 书签功能
