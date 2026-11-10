"""婚纱写真照相馆：固定话术。宿主原样转述，不改写。"""

from urllib.parse import unquote

SKILL_NAME = '婚纱写真照相馆'

WELCOME = '欢迎使用WorkBuddy官方认证技能 ' + SKILL_NAME + '。'
CLOSE_WITH_NEED = '这个方向可以吗？'
CLOSE_OPEN = '你想从哪个方向开始？'
DEMO_INTRO = '都是效果示例图，不是你的真实结果。'
DEMO_UNAVAILABLE = '这次暂时没能展示示例图。'
PRICE_ANSWER = '按张计费，档位和金额在充值页上，确认方案后我带你过去。'

REASSURE_SAVED = '你确认的方案已经存好了，不用重新描述。'
REASSURE_FREE = '到这一步为止，没有产生任何扣费。'
CROSS_SKILL = '已经在其他技能开通过账户？同一账户的通用次数在已接入的技能间共享，这里不用重新付费。'
DECLINE = '没问题。等你需要图片的时候随时叫我。'
ONE_CHANGE = '想改的地方请每次只说一件事，一句话里有多个修改时，我会拆成几次依次完成。'
NO_REPEAT = '等待期间请不要重复发起，也不要换个说法重新提交，重复提交可能会重复计费。'
ORIGINAL_KEPT = '你发来的原照片没有改动，结果另存为新文件。'
SHAPE_NAMES = {'portrait': '竖版 2:3', 'landscape': '横版 3:2', 'square': '方图 1:1'}
LIKENESS = '会尽力保持五官与身份特征，细节差异可能存在；AI 生成的效果可能与本人有差异，请以你自己看过满意为准。'


def _reassure():
    return [REASSURE_SAVED, REASSURE_FREE]


def first_turn_close(has_need):
    """首轮收尾：不含链接、账户、价格。"""
    return CLOSE_WITH_NEED if has_need else CLOSE_OPEN


def _who(people):
    return '你们两位' if people == 2 else '你'


def plan_summary(series, title, shape_name, people):
    who = '两人同框' if people == 2 else '单人'
    return '「' + title + '」' + series + '照，' + who + '，' + shape_name + '，1 张'


def confirm_paid(summary, wait_text, people=1):
    """方案与付费确认：只有用户明确肯定回答后才能继续。"""
    consent = ('照片里的两位都是成年人，并且都同意用这张照片制作' if people == 2
               else '照片里是你本人，或已经征得本人同意的成年人')
    return '\n'.join([
        '我按这个方案做：' + summary + '。',
        '预计等待' + wait_text + '。' + LIKENESS,
        '开始前需要你确认两件事：',
        '1. ' + consent + '，同意把这张照片发送去处理，只用于本次制作；',
        '2. 同意按张计费开始制作，费用以充值页和本次服务记录为准。',
        '两件都同意的话，回复「确认开始」。',
    ])


def people_unsupported(title):
    return '「' + title + '」只做单人照。可以换一张单人照片，或者改做婚纱主题的两人同框照。'


def auth(url, expires_hint='几分钟'):
    return '\n'.join([
        '我这边已经把你确认的写真方案存好了。首次出图需要先完成一次授权，授权本身不扣费。',
        '',
        '### 现在需要你做的',
        '1. 点开授权链接：[打开授权页](' + url + ')',
        '2. 按页面提示完成确认，不用手机号、不用验证码，也不用填写任何密钥。',
        '3. 链接' + expires_hint + '内有效；页面打不开或链接过期了，跟我说一声「重新取链接」，方案不受影响。',
        '',
        '做完跟我说一声「好了」，我接着按你确认的方案制作。',
        CROSS_SKILL,
    ] + _reassure())


def auth_short(url):
    return '\n'.join([
        '新的授权链接：[打开授权页](' + url + ')',
        '页面打不开就再跟我说一声，我重新取一个。',
    ] + _reassure())


def auth_pending():
    return '\n'.join([
        '我刚查了一次，还没看到授权完成。',
        '',
        '### 现在需要你做的',
        '1. 如果页面还开着，请在页面上完成确认。',
        '2. 页面打不开或已经过期，跟我说「重新取链接」。',
        '',
        '做完说一声「好了」，我再查一次，然后按你确认的方案继续。',
    ] + _reassure())


def final_step(url):
    return '\n'.join([
        '账户已经关联好了，你确认的方案也存着。',
        '只剩最后一步：选个套餐补充余额，选完我立刻按你确认的方案出图。',
        '',
        '### 现在需要你做的',
        '1. 打开充值页：[打开充值页](' + url + ')',
        '2. 档位和金额都在页面上，按需选择。',
        '3. 页面打不开或链接过期了，跟我说「重新取充值链接」。',
        '',
        '付款后即时到账，跟我说「继续」，方案不用重说，我接着做。',
    ] + _reassure())


def topup_ask():
    """任务中途余额不足：先问，同意后才取链接。"""
    return '\n'.join([
        '这张还没有开始生成，这次没有扣次数，任务已经保留。',
        '当前余额不够做这一张。要我打开充值页吗？',
    ] + _reassure())


def topup_link(url):
    return '\n'.join([
        '充值页在这里：[打开充值页](' + url + ')',
        '页面打开不等于已经下单，充不充、充多少都由你决定。',
        '页面打不开或过期了，跟我说「重新取充值链接」。付款到账后说「继续」，我按原方案接着做。',
    ])


def paid_confirmed(remaining):
    """只在查到可用次数后使用。"""
    return '我刚查了一次，账户剩余可用次数 ' + str(remaining) + ' 次。说一声「继续」，我按原方案接着做。'


def paid_not_yet(url=None):
    """用户说已付款但还没查到到账：如实说，不当作已到账。"""
    lines = ['我刚查了一次，还没看到这笔到账，没有扣任何次数。图片需求已保留，稍等一下再说「付好了」或「继续」，我再查。']
    if url:
        lines.append('还没付款的话，充值页在这里：[打开充值页](' + url + ')，页面打不开或过期了，跟我说「重新取充值链接」。')
    return '\n'.join(lines)


def credits_not_yet():
    return '我刚查了一次，还没看到这笔到账。图片需求已保留，稍等一下再说「继续」，我再查。'


def start_recap(title, series, shape_name, people, count=1):
    who = '两人同框' if people == 2 else '单人'
    return ('开始制作：「' + title + '」' + series + '照，' + who + '，' + shape_name + '，共' + str(count) +
            '张，尽量保持' + _who(people) + '的五官和身份特征。' + NO_REPEAT)


def _link_label(link):
    name = unquote(link.rsplit('/', 1)[-1])
    return ''.join('\\' + c if c in '[]\\*_`' else c for c in name)


def delivery(links, remaining, first_time, title, people=1, size_note='', gallery_link=''):
    """links / gallery_link 必须是已做 Markdown 安全编码的链接目标（studio.md_safe_path）。"""
    lines = ['做好了：']
    for p in links:
        lines.append('- [' + _link_label(p) + '](' + p + ')')
    if gallery_link:
        lines.append('- [全部结果一览](' + gallery_link + ')')
    lines.append('这次做成了「' + title + '」主题，换了服装、背景和光影，尽量保持' + _who(people) +
                 '的五官、发际线和肤色；AI 生成的效果可能与本人有差异，请放大看看脸部和手部。')
    if size_note:
        lines.append(size_note)
    lines.append(ORIGINAL_KEPT)
    if remaining is None:
        lines.append('本次费用以服务记录为准。')
    else:
        lines.append('本次费用以服务记录为准，剩余 ' + str(remaining) + ' 次。')
    if first_time:
        lines.append('想调整直接说，比如「背景换成海边」「改成横版」「换成秀禾服」。' + ONE_CHANGE + '需要重新生成的调整可能再次按张计费，我会先跟你确认。')
    return '\n'.join(lines)


def photo_changed():
    return ('你确认时用的那张照片，文件后来有了变化。为了不做错照片，这次还没有开始制作，没有产生任何扣费。'
            '请把要用的照片再发我一次，我按原来的方向重新跟你确认后再开始。')


def size_mismatch(actual, requested):
    return '这次实际出图尺寸是 ' + actual + '，不是 ' + requested + '。画面比例以实际文件为准，需要固定尺寸时可以再裁切。'


def failure(reason_kind, charge_kind):
    reason = {
        'busy': '服务正在处理较多请求',
        'network': '网络连不上',
        'stale': '刚取到的链接已经过期，这一步还没完成',
        'rejected': '这张照片暂时无法按这个主题处理',
        'input': '照片文件不符合要求',
    }[reason_kind]
    charge = {
        'not_started': '这次还没有开始生成，没有扣次数。',
        'record': '费用以服务记录为准。',
    }[charge_kind]
    return '这次没有拿到图——' + reason + '。' + charge + '稍后想再试，直接告诉我「重新生成」。'


def busy_kept():
    return '这次没有拿到图——服务正在处理较多请求。这次还没有开始生成，没有扣次数，任务已保留。稍后说「继续」，我按原方案接着做。'


def still_processing():
    return '还在处理中，任务已保留。稍后说「继续」，我接着查这一张，不会重新提交。' + NO_REPEAT


def progress_unknown():
    return '当前进度未能确认，费用以服务记录为准。任务已保留，稍后说「继续」，我接着查这一张，请不要重复生成。'


def download_incomplete():
    return '图片下载暂时未完成，费用以服务记录为准，请不要重复生成。稍后说「继续」，我再取一次这张图。'


def credentials_reset():
    return '登录状态已过期，我已清除旧的登录信息。' + REASSURE_SAVED + '接下来重新授权一次即可继续，授权本身不扣费。'


def account_summary(remaining, cards=None, total=None):
    lines = ['剩余可用次数：' + str(remaining) + ' 次']
    if cards is None:
        lines.append('消费记录这次没取到，稍后说「消费记录」我再查一次。')
    elif not cards:
        lines.append('还没有消费记录。')
    else:
        lines.append('最近记录：')
        lines += cards
        lines.append('共 ' + str(total) + ' 条，回复「查看所有」可看全部。')
    lines.append(HISTORY_SCOPE)
    lines.append('需要补充次数时，回复「充值」我为你打开充值页。')
    return '\n'.join(lines)


HISTORY_SCOPE = '记录包含同一账户在已接入技能里的通用次数使用情况。'
_JOB_STATUS = {'succeeded': '已完成', 'pending': '处理中', 'needs_review': '核对中', 'failed': '未完成'}


def history_card(when, content, charged, reserved, refunded, status):
    if isinstance(charged, int):
        fee = '未扣次' if charged == 0 else '扣 ' + str(charged) + ' 次'
    elif isinstance(reserved, int) and reserved > 0:
        fee = '预留 ' + str(reserved) + ' 次，完成后结算'
    else:
        fee = '扣次以服务记录为准'
    if isinstance(refunded, int) and refunded > 0:
        fee += '，已退回 ' + str(refunded) + ' 次'
    return '- ' + when + ' · ' + content + '\n  ' + fee + ' · ' + _JOB_STATUS.get(status, '其他')


def history_page(cards, total, page, has_more):
    if not cards:
        return '这一页没有记录，共 ' + str(total) + ' 条。'
    lines = ['消费记录（第 ' + str(page) + ' 页，共 ' + str(total) + ' 条）：'] + cards
    if has_more:
        lines.append('还有更多，回复「下一页」继续看。')
    lines.append(HISTORY_SCOPE)
    return '\n'.join(lines)


def history_unavailable():
    return '消费记录这次没取到，稍后说「消费记录」我再查一次。'


_CATEGORY = {'billing': '费用与次数', 'image_quality': '出图效果', 'workflow': '使用流程', 'suggestion': '建议与表扬', 'other': '其他'}
_TICKET_STATUS = {'open': '已受理，等待处理', 'in_progress': '处理中', 'resolved': '已处理'}


def _due(due_text):
    if due_text:
        return '预计处理时间：' + due_text + ' 前。'
    return '目前没有承诺具体处理时限，有回复后说「查工单」就能看到。'


def ticket_created(ticket_id, category, due_text):
    return '\n'.join([
        '你的反馈已经提交。',
        '反馈编号：' + ticket_id + '（' + _CATEGORY.get(category, '其他') + '）',
        _due(due_text),
        '之后说「查工单」就能看到处理进度和回复。提交反馈不扣次数。',
    ])


def ticket_view(ticket_id, category, status, reply, due_text):
    lines = ['反馈编号：' + ticket_id + '（' + _CATEGORY.get(category, '其他') + '）',
             '处理状态：' + _TICKET_STATUS.get(status, '处理中')]
    if reply:
        lines.append('回复：' + reply)
    else:
        lines.append('暂时还没有回复。')
        lines.append(_due(due_text))
    return '\n'.join(lines)


def tickets_none():
    return '这台设备上还没有提交过反馈。想反馈问题或提建议，直接告诉我就行。'


def ticket_not_found():
    return '没有找到这个反馈编号，请核对一下编号；也可以直接说「查工单」查看这台设备提交过的反馈。'


def feedback_saved(reason):
    head = {
        'no_account': '这台设备还没有关联账户，反馈单需要账户才能提交。',
        'busy': '服务正在处理较多请求，反馈这次没能提交。',
        'network': '网络暂时连不上，反馈这次没能提交。',
    }.get(reason, '反馈这次没能提交。')
    tail = '完成授权后说「提交反馈」，我再交一次。' if reason == 'no_account' else '稍后说「提交反馈」，我再交一次。'
    return head + '你的原话已经在本机记下，不用重说；' + tail + '提交反馈不扣次数。'


def feedback_nothing_pending():
    return '没有待提交的反馈。'


def ticket_lookup_failed(reason_kind):
    head = '网络暂时连不上' if reason_kind == 'network' else '服务正在处理较多请求'
    return head + '，这次没查到反馈进度。稍后说「查工单」我再查一次。'


def too_frequent():
    return '查询太频繁了，请稍等一分钟再试。'


def account_link(url, retry_word='充值'):
    """本机还没有账户的新用户要充值、付费链接或查账户时：给关联链接，不回死胡同。"""
    return '\n'.join([
        '这台设备还没有关联账户，先关联一次就能充值和查账户。',
        '',
        '### 现在需要你做的',
        '1. 点开关联链接：[关联账户](' + url + ')',
        '2. 扫码确认后会直接进入充值页，档位和金额都在页面上，按需选择；关联本身不扣费。',
        '3. 链接几分钟内有效；页面打不开或过期了，再跟我说一次「' + retry_word + '」，我重新取链接。',
        '',
        CROSS_SKILL,
    ])


def account_failure(reason_kind, retry_word='充值'):
    """账户类命令没拿到结果：按网络/繁忙如实说明，不猜原因。"""
    reason = {
        'network': '网络暂时没连上',
        'busy': '服务正在处理较多请求，这一步还没完成',
        'stale': '刚取到的链接已经过期，这一步还没完成',
    }[reason_kind]
    return reason + '，没有扣任何次数，稍后再说一次「' + retry_word + '」。'


def account_missing():
    return '这台设备上还没有关联账户。确认好写真方案后，我会带你完成一次授权，授权本身不扣费。'


def input_error(filename, problem):
    return '照片「' + filename + '」' + problem + '，这次没有发送，也没有扣次数。换一张清晰的 PNG 或 JPG 照片发我就行。'


def refuse_misuse():
    return ('这个需求我不能处理：本技能只用你本人或已获本人同意的成年人照片制作婚纱照和写真，'
            '不处理未成年人的照片，不换脸，也不把照片里没有的人合成进来。')


def favorite_done():
    return '已收藏，以后问婚纱照、写真问题会优先由' + SKILL_NAME + '接待。想取消时说「取消收藏' + SKILL_NAME + '」即可。'


def favorite_unsupported():
    return '当前环境暂不支持收藏技能。'
