#!/usr/bin/env python
# encoding:utf-8
'''
试卷渲染
'''
import re
import time
import sys
import os
reload(sys)
sys.setdefaultencoding('utf-8')

import copy
import logging
import urllib2
from bson.objectid import ObjectId
from pymongo import MongoClient

template = ur'''% !TEX encoding=utf8
% !TEX program=xelatex
\documentclass{article}'''u'''
\\usepackage{xeCJK}
\\usepackage{varwidth}
\\usepackage{amsmath, amssymb, yhmath}
\\usepackage{mhchem}
\\usepackage{graphicx}
\\usepackage{mdwlist}
\\usepackage{enumerate}
\\usepackage{pifont,arcs}
\\usepackage{ifthen,CJKnumb}
\\usepackage[paperwidth=195mm,paperheight=270mm,left=12mm,right=14mm,top=16mm,bottom=4mm,includefoot]{geometry}'''ur'''
%%\setCJKmainfont{SimSun}
\linespread{1.3}
\setlength{\fboxsep}{0pt}
\setlength{\fboxrule}{0.4pt}
\newcommand{\dq}{\mbox{(\qquad)}}
\newcommand{\dd}{\mbox{\rule[-.2ex]{4em}{.5pt}}}
\newcommand{\fourch}[4]
{\newline \begin{tabular}{*{4} {@{} p{0.25\textwidth}}} A. #1 & B. #2 & C. #3 & D. #4 \end{tabular}}
\newcommand{\twoch}[4]
{\newline \begin{tabular}{*{2} {@{} p{0.5\textwidth}}} A. #1 & B. #2\\ \end{tabular}
\begin{tabular}{*{2} {@{} p{0.5\textwidth}}}C. #3 & D. #4 \end{tabular}}
\newcommand{\onech}[4]{\newline  A. #1 \\ B. #2 \\ C. #3 \\ D. #4}
%\newcommand{\imgch}[4]{
%\newline \begin{tabular}{cccc}  \fbox{#1} &  \fbox{#2} & \fbox{#3} &  \fbox{#4} \\ A & B & C & D \end{tabular}}
\newlength{\cha}
\newlength{\chb}
\newlength{\chc}
\newlength{\chd}
\newlength{\maxw}
\newcommand{\imgch}[8]{
    \settowidth{\cha}{#1}
    \settowidth{\chb}{#3}
    \settowidth{\chc}{#5}
    \settowidth{\chd}{#7}
    \addtolength{\cha}{\chb}
    \addtolength{\cha}{\chd}
    \addtolength{\cha}{\chc}
    \ifthenelse{\lengthtest{\cha = 0mm}}
    {%then no text in img_opts
    \newline 
    \begin{tabular}{cccc}  
    \fbox{#2} &  \fbox{#4} & \fbox{#6} &  \fbox{#8} \\
    A & B & C & D 
    \end{tabular}
    }
    {%else some text in img_opts
    \newline 
    \begin{tabular}{*{4} {@{} p{0.24\textwidth}}c}
    \centering #2 & \centering #4 & \centering #6 & \centering #8 &\\
    \parbox{0.23\textwidth}{ \centering #1} & \parbox{0.23\textwidth}{\centering #3} & \parbox{0.23\textwidth}{\centering #5} &  \parbox{0.23\textwidth}{\centering #7} & \\
    \centering A & \centering B & \centering C & \centering D   &\\
    \end{tabular}
    }
    }
\setlength{\parindent}{0em}
\setlength{\parskip}{1em}
\newcommand{\ch}[8]{
    \settowidth{\cha}{A. #1}
    \settowidth{\chb}{B. #2}
    \settowidth{\chc}{C. #3}
    \settowidth{\chd}{D. #4}\setlength{\maxw}{\cha}
    \ifthenelse{\lengthtest{\chb > \maxw}}{\setlength{\maxw}{\chb}}{}
    \ifthenelse{\lengthtest{\chc > \maxw}}{\setlength{\maxw}{\chc}}{}
    \ifthenelse{\lengthtest{\chd > \maxw}}{\setlength{\maxw}{\chd}}{}
    \ifthenelse{\lengthtest{\maxw > 0.48\textwidth}}
    {\onech{#1}{#3}{#5}{#7}}
    {\ifthenelse{\lengthtest{\maxw >0.24\textwidth}}{\twoch{#1}{#3}{#5}{#7}}{\fourch{#1}{#3}{#5}{#7}}}}
\newcounter{ns}
\newcounter{nq}
\newcounter{nqq}[nq]
\newcounter{nqqq}[nqq]
\newcommand{\wq}{
    \stepcounter{nq}
    \thenq.\hspace{.6em}}
\newcommand{\wqq}{\stepcounter{nqq}\item[(\thenqq)]}
\newcommand{\wqqq}{\stepcounter{nqqq}\item[(\roman{nqqq})]}
\newcommand{\wns}{\stepcounter{ns}\CJKnumber{\thens}、}
\newcommand{\ws}[2]{\begin{minipage}[t]{\textwidth} {\heiti \wns #1 } #2 \end{minipage} }
\newlength{\indexlength}
\newlength{\contentlength}
\newlength{\subcontentlength}
\setlength{\indexlength}{1.5em}
\setlength{\contentlength}{\textwidth}
\setlength{\subcontentlength}{\textwidth}
\addtolength{\contentlength}{-1em}
\addtolength{\subcontentlength}{-3em}
\newenvironment{question}{%
    \begin{minipage}[t]{\indexlength}\wq\end{minipage}\begin{minipage}[t]{\contentlength}
    }{%
    \end{minipage}\par
    }
\newenvironment{subquestions}{\begin{enumerate*}}{\end{enumerate*}}
\newenvironment{subsubquestions}{\begin{enumerate*}}{\end{enumerate*}}
\renewcommand{\cong}{\text{\raisebox{-0.2em}{\includegraphics[height=1em]{../imgs/U+224C.pdf}}}}
\renewcommand{\parallel}{\text{\raisebox{-0.2em}{\includegraphics[height=1em]{../imgs/U+2225.pdf}}}}
\begin{document}
'''


def str2latex(ori):
    def array_mathmode(s):
        def _array_math_display(s):
            s = re.sub(
                ur'\\begin\s?{array}[\s\S]*?\\end\s?{array}', lambda x: ur'\[%s\]' % x.group(), s)
            return s

        def _dealdisplay(s):
            stop = s.find(ur'\]')
            if stop == -1:
                s = _array_math_display(s)
            else:
                math = s[:stop]
                text = s[stop:]
                text = _array_math_display(text)
                s = math + text
            return s

        def _dealinline(s):
            stop = s.find(ur'\)')
            if stop == -1:
                s = re.split(ur'(?<!\\)\\\[', s)
                for idx, str in enumerate(s, start=0):
                    s[idx] = _dealdisplay(str)
                s = ur'\['.join(s)
            else:
                math = s[:stop]
                k = s[stop:]
                k = re.split(ur'(?<!\\)\\\[', k)
                for idx, str in enumerate(k, start=0):
                    k[idx] = _dealdisplay(str)
                k = ur'\['.join(k)
                s = math + k
            return s

        s = re.split(ur'(?<!\\)\\\(', s)
        for idx, str in enumerate(s, start=0):
            s[idx] = _dealinline(str)
        s = ur'\('.join(s)
        return s


    def cn_in_mathmode(s):  # by ningshuo

        def _deal_mathmode(s):
            s = re.sub(ur'[\u4e00-\u9fa5]+',
                       lambda x: ur'\text{%s}' % x.group(), s)
            return s

        def _deal_textmode(s):

            s = s.replace(u'\n', u'\\\\\n')

            return s

        def _dealdisplay(s):
            stop = s.find(ur'\]')
            if stop == -1:
                s = _deal_textmode(s)
            else:
                math = s[:stop]
                math = _deal_mathmode(math)
                text = s[stop:]
                text = _deal_textmode(text)
                s = math + text
            return s

        def _dealinline(s):
            stop = s.find(ur'\)')
            if stop == -1:
                s = re.split(ur'(?<!\\)\\\[', s)
                for idx, str in enumerate(s, start=0):
                    s[idx] = _dealdisplay(str)
                s = ur'\['.join(s)
            else:
                math = s[:stop]
                math = _deal_mathmode(math)
                k = s[stop:]
                k = re.split(ur'(?<!\\)\\\[', k)
                for idx, str in enumerate(k, start=0):
                    k[idx] = _dealdisplay(str)
                k = ur'\['.join(k)
                s = math + k
            return s

        s = array_mathmode(s)
        s = re.split(ur'(?<!\\)\\\(', s)
        for idx, str in enumerate(s, start=0):
            s[idx] = _dealinline(str)
        s = ur'\('.join(s)
        s = s.replace(u'\\\\\n\[', u'\n\[')
        s = s.replace(u'\]\\\\\n', u'\]\n')
        return s

#==================================================================
    def array_col_correction(x):
        x.group(0).split('\\\\')[0]
        col_num = len(re.findall(ur'(?<!\\)&', x.group(0).split('\\\\')[0]
                                 )) + 1
        col_arg_center = 'c' * col_num
        col_arg_left = 'l' * col_num
        col_arg_lined = ur'|' + ur'c|' * col_num
        s = re.sub(ur'{c+}', '{%s}' % col_arg_center, x.group(0))
        s = re.sub(ur'{\|c\|.*?}', '{%s}' % col_arg_lined, s)
        s = re.sub(ur'{l+}', '{%s}' % col_arg_left, s)
        return s

    def split_mathmode(x):
        x = re.sub(ur'split', ur'aligned', x.group(0))
        return x

    def unicode_2_latex(s):
        unicode2latex = [
            (ur'\u2460', ur'\text{\ding{172}}'),
            (ur'\u2461', ur'\text{\ding{173}}'),
            (ur'\u2462', ur'\text{\ding{174}}'),
            (ur'\u2463', ur'\text{\ding{175}}'),
            (ur'\u2464', ur'\text{\ding{176}}'),
            (ur'\u2465', ur'\text{\ding{177}}'),
            (ur'\u2466', ur'\text{\ding{178}}'),
            (ur'\u2467', ur'\text{\ding{179}}'),
            (ur'\u2468', ur'\text{\ding{180}}'),
            (ur'\u2469', ur'\text{\ding{181}}'),
            (ur'\u2160', ur'\mathrm{I}'),
            (ur'\u2161', ur'\mathrm{II}'),
            (ur'\u2162', ur'\mathrm{III}'),
            (ur'\u2163', ur'\mathrm{IV}'),
            (ur'\u2164', ur'\mathrm{V}'),
            (ur'\u2165', ur'\mathrm{VI}'),
            (ur'\u2166', ur'\mathrm{VII}'),
            (ur'\u2167', ur'\mathrm{VIII}'),
            (ur'\u2168', ur'\mathrm{IX}'),
            (ur'\u2169', ur'\mathrm{X}'),
            (ur'\overparen', ur'\wideparen'),
            (ur'\lt', ur'<'),
            (ur'\gt', ur'>'),
            (ur'\u007f', ur''),
            (ur'{align}', ur'{matrix}'),
            (ur'{split}', ur'{aligned}'),
            (ur'\uff1d', ur'='),
            (ur'\Omega', ur'\text{$\Omega$}'),
            (ur'\style{font-family:Times New Roman}{g}', ur'\textsl{g}'),
            (ur'\uFF1E', ur'>'),
            (ur'\uFF1C', ur'<'),
            (ur'\u00A0', ur' '),
            (ur'\uFF0B', ur'+')
        ]
        for uni, latex in unicode2latex:
            s = s.replace(uni, latex)
        return s

    ori = unicode_2_latex(ori)
    ori = re.sub(ur'(?<!\\)%', '\%', ori)
    ori = array_mathmode(ori)
    ori = cn_in_mathmode(ori)
    ori = re.sub(
        ur'\\begin\s?{array}[\s\S]*?\\end\s?{array}', array_col_correction, ori)
    ori = re.sub(ur'\u005f\u005f+', ur'\\dd ', ori)
    # ori = re.sub(ur'{\\rm\s*\\Omega}', ur'\\Omega', ori)
    # ori = re.sub(ur'{\\rm\s*k*\\Omega}', ur'{\\rm k}\\Omega', ori)
    return ori


def punc_in_img(s):  # by ningshuo
    def _deal(s):
        stop = s.find(ur'[[/img]]')
        assert stop != -1
        result = re.sub(ur'\uff0e',
                        ur'.', s[:stop])
        result = re.sub(ur'\uff1a',
                        ur':', result)
        result = re.sub(ur'\uff0c',
                        ur',', result)
        return result + s[stop:]

    s = re.split(ur'\[\[img\]\]', s)
    for idx, str in enumerate(s[1:], start=1):
        s[idx] = _deal(str)
    s = ur'[[img]]'.join(s)
    return s


def get_opts_head(opts):
    opt_imgs_cnt = 0
    for opt in opts:
        opt = punc_in_img(opt)
        opt_imgs = re.findall(img_file_re, opt)
        if opt_imgs:
            opt_imgs_cnt += 1
    if opt_imgs_cnt == 4:
        return '\\imgch'
    else:
        return '\\ch'


def get_opt_img(opt, img_width):
    opt = punc_in_img(opt)
    opt_imgs = re.findall(img_file_re, opt)
    opt_img = ''
    if opt_imgs:
        for img_file in opt_imgs:
            if not os.path.isfile('{}{}'.format(img_path, img_file)):
                img_f = open('{}{}'.format(img_path, img_file), 'w')
                img_f.write(urllib2.urlopen(
                    '{}{}'.format(img_url, img_file)).read())
            opt_img = '\\includegraphics[width={}\\textwidth]{{{}{}}}'.format(
                img_width, img_path, img_file)
    opt = re.sub(img_re3, '', opt)
    opt = re.sub(ur'\n', '', opt)
    return [opt, opt_img]


def item_latex_render(item_id):
    tex = '%% {} \n '.format(item_id)
    tex += '\\fbox{\n \\begin{varwidth}{\\textwidth} \\begin{question}\n'
    item = db.item.find_one({'_id': item_id})
#================================================选择题======================================    
    if item['data']['type'] in [1001, 2001,4001]:
        tex += '%s \n' % str2latex(item['data']['qs'][0]['desc'].replace('[[nn]]', '\\dq '))
        opts = item['data']['qs'][0]['opts']
        opt_tex = get_opts_head(opts)
        for opt in opts:
            opt = get_opt_img(opt, 0.222)
            opt_tex += '{%s}{%s}' % (str2latex(opt[0]),str2latex(opt[1]))
        tex += opt_tex
#================================================填空题======================================   
    elif item['data']['type'] in [1002, 2002]:
        tex += '%s \n' % str2latex(item['data']['qs'][0]['desc'].replace('[[nn]]', '\\dd '))
#================================================解答题======================================   
    elif item['data']['type'] in [1003, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 0]:        
        if len(item['data']['stem']) == 0:
            if len(item['data']['qs']) == 1:
                tex += u'%s \n ' % str2latex(item['data']['qs'][0]['desc'].replace('[[nn]]', '\\dd '))
            else:
                tex += u'\\begin{subquestions} \n' 
                for z in range(len(item['data']['qs'])):
                    tex += u'\\wqq %s \n' %  str2latex(item['data']['qs'][z]['desc'].replace('[[nn]]', '\\dd '))
                    if 'qs' in item['data']['qs'][z]:
                        tex += u'\\begin{subsubquestions} \n'
                        for qs_qs in item['data']['qs'][z]['qs']:
                            tex += u'\wqqq {} \n'.format(str2latex(qs_qs['desc'].replace('[[nn]]', '\\dd ')))
                        tex += u'\\end{subsubquestions} \n'
                tex += '\\end{subquestions} \n '
        else:
            tex += u'%s \n' % str2latex(item['data']['stem'].replace('[[nn]]', '\\dd '))
            if (len(item['data']['qs']) == 1) and (len(item['data']['qs'][0]['desc']) == 0):
                tex += u'\n'
            else:
                tex += '\\begin{subquestions} \n'
                for z in range(len(item['data']['qs'])):
                    if len(item['data']['qs'][z]['desc']) != 0:
                        tex += u'\\wqq %s \n' %  str2latex(item['data']['qs'][z]['desc'].replace('[[nn]]', '\\dd '))     
                        if 'qs' in item['data']['qs'][z]:
                            tex += u'\\begin{subsubquestions} \n'
                            for qs_qs in item['data']['qs'][z]['qs']:
                                tex += u'\wqqq {} \n'.format(str2latex(qs_qs['desc'].replace('[[nn]]', '\\dd ')))
                            tex += u'\\end{subsubquestions} \n'
                tex += '\\end{subquestions} \n'

    tex += u'\\end{question} \n \\end{varwidth} \n }\\\\'
    # desc = get_img(desc, 0.5)
    # qss = re.sub(img_re2, '', qss)
    tex = re.sub(img_re2, '', tex)

    # if len(qss) == 0:
    #     item_tex = u'%{}\n{}\n\n{}'.format(
    #     item_id, desc,  opt_tex)
    # else:
    #     item_tex = u'%{}\n{} \n {}\n{}'.format(
    #     item_id, desc, qss, opt_tex)
    # item_tex = item_tex.replace(u'\n\n', u'\n')
    return tex


def physics_paper_render(paper):

    def _deal_paper_head(paper):
        return '% {id}\n\\begin{{center}}\n{paper_name}\n\\end{{center}}'.format(id=paper['_id'], paper_name=paper['name'])

    def _deal_part_head(part):
        item_type = itmtyp_2_name[part[0]['type']]
        return u'\\wns {} \\\\*\n'.format(item_type)

    result_tex = template
    result_tex += _deal_paper_head(paper)
    for part in paper['parts']:
        result_tex += _deal_part_head(part)
        for item in part:
            result_tex += item_render(item['item_id'])

    result_tex += '\\end{document}'
    return result_tex
""" 
=== Setting =============================================================
"""

client = MongoClient('10.0.0.168', 27017)
dbname = 'chemistry'
db = client[dbname]

pdf_width = u'\\textwidth'
img_url = 'http://www.kuailexue.com/data/img/'

itmtyp_2_name = {1001: '选择题',
                 1002: '填空题',
                 1003: '解答题',
                 2001: '选择题',
                 2002: '填空题',
                 2003: '解答题',
                 2004: '实验题',
                 2005: '模块选做题',
                 2006: '作图题',
                 2007: '科普阅读题',
                 2008: '简答题',
                 2009: '计算题',
                 2010: '综合应用题',
                 }

paper_id = ObjectId("572abb4bbbddbd4d2dbd89dc")
paper = db.papers.find_one({'_id': paper_id})
paper_path = '../papers/'
item_path = '../items/'
img_path = '../imgs/'
img_re2 = re.compile(ur'\n?\[\[img\]\].*?\[\[/img\]\]')
img_re3 = re.compile(ur'\[\[img\]\].*?\[\[/img\]\]')
img_file_re = re.compile(ur'\w+\.(?:png|jpg|gif|bmp)')

for path in [paper_path, item_path, img_path]:
    if os.path.exists(path):
        pass
    else:
        os.makedirs(path)
#=====================================单题测试=======================
def do_items(items, subject):
    tex = template
    dbname = subject
    for item in items:
        print item['_id']
        tex += item_latex_render(item['_id'])
    tex += u'\\end{document}'
    return tex

skip = 4540
limit = 20
items = list(db.item.find({'status': {'$in': [40, 50, 60, 70]}}).skip(skip).limit(limit))
subject = 'physics'
path = paper_path
f = open('{}.tex'.format(skip), 'w')
f.write(do_items(items, subject))
f.close

print skip


item_ids = [
    '562739ec5417d174cb1a3de5',
    '560b8cd15417d174cc8280a4',
]

# f = open('{path}{name}.tex'.format(path=paper_path, name=paper_id), 'w')



