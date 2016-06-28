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

client = MongoClient('10.0.0.100', 27017)
dbname = 'klx_ph'
db = client[dbname]

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
\linespread{1.5}
\setlength{\fboxsep}{0pt}
\setlength{\fboxrule}{0.4pt}
\newcommand{\dq}{\mbox{(\qquad)}}
\newcommand{\dd}{\mbox{\rule[-.2ex]{4em}{.5pt}}}
\newcommand{\fourch}[4]
{\begin{tabular}{*{4} {@{} p{0.25\textwidth}}} A. #1 & B. #2 & C. #3 & D. #4 \end{tabular}}
\newcommand{\twoch}[4]
{\begin{tabular}{*{2} {@{} p{0.5\textwidth}}} A. #1 & B. #2\\ \end{tabular}
\begin{tabular}{*{2} {@{} p{0.5\textwidth}}}C. #3 & D. #4 \end{tabular}}
\newcommand{\onech}[4]{ A. #1 \\ B. #2 \\ C. #3 \\ D. #4}
\newcommand{\imgch}[4]
{\begin{tabular}{cccc}  \fbox{#1} &  \fbox{#2} & \fbox{#3} &  \fbox{#4} \\ A & B & C & D \end{tabular}}
\newlength{\cha}
\newlength{\chb}
\newlength{\chc}
\newlength{\chd}
\newlength{\maxw}
\setlength{\parindent}{0em}
\newcommand{\ch}[4]
{
\settowidth{\cha}{A. #1}
\settowidth{\chb}{B. #2}
\settowidth{\chc}{C. #3}
\settowidth{\chd}{D. #4}\setlength{\maxw}{\cha}
\ifthenelse{\lengthtest{\chb > \maxw}}{\setlength{\maxw}{\chb}}{}
\ifthenelse{\lengthtest{\chc > \maxw}}{\setlength{\maxw}{\chc}}{}
\ifthenelse{\lengthtest{\chd > \maxw}}{\setlength{\maxw}{\chd}}{}
\ifthenelse{\lengthtest{\maxw > 0.48\textwidth}}
{\onech{#1}{#2}{#3}{#4}}
{\ifthenelse{\lengthtest{\maxw >0.24\textwidth}}{\twoch{#1}{#2}{#3}{#4}}{\fourch{#1}{#2}{#3}{#4}}}}
\newcounter{ns}
\newcounter{nq}
\newcounter{nqq}[nq]
\newcommand{\wq}{\stepcounter{nq}\thenq.\quad}
\newcommand{\wqq}{\stepcounter{nqq}(\thenqq).}
\newcommand{\wns}{\noindent \stepcounter{ns}\CJKnumber{\thens}、}
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
\end{minipage}\\
}
\newenvironment{subquestion}{%
\begin{minipage}[t]{\indexlength}\wqq\end{minipage}\begin{minipage}[t]{\subcontentlength}
}{%
\end{minipage}\\ \\
}
\renewcommand{\cong}{\text{\raisebox{-0.2em}{\includegraphics[height=1em]{../imgs/U+224C.pdf}}}}
\renewcommand{\parallel}{\text{\raisebox{-0.2em}{\includegraphics[height=1em]{../imgs/U+2225.pdf}}}}
\begin{document}
'''


def str2latex(ori):
    def array_in_mathmode(s):  # by ningshuo
        def _deal(s, math_end):
            stop = s.find(ur'\)')
            print stop
            if stop == -1:
                s = re.sub(ur'\\begin\s?{array}', ur'\[\\begin{array}', s)
                s = re.sub(ur'\\end\s?{array}', ur'\\end{array}\]', s)
            else:
                s = s[
                    :stop] + re.sub(ur'\\begin\s?{array}', ur'\[\\begin{array}', s[stop:])
            return s

        s = re.split(ur'(?<!\\)\\\(', s)
        show_pretty_dict(s)
        for idx, str in enumerate(s, start=0):
            s[idx] = _deal(str, ur'(?<!\\)\\\)')
        s = ur'\('.join(s)
        return s

    def cn_in_mathmode(s):  # by ningshuo
        def _deal(s, math_end):
            stop = s.find(math_end)
            assert stop != -1
            return re.sub(ur'[\u4e00-\u9fa5]+',
                          lambda x: ur'\text{%s}' % x.group(), s[:stop]) + s[stop:]

        math_mode_delimiter = [
            (ur'\(', ur'\)'),
            (ur'\[', ur'\]'),
        ]
        for math_begin, math_end in math_mode_delimiter:
            s = re.split(ur'(?<!\\)\\%s' % math_begin, s)
            for idx, str in enumerate(s[1:], start=1):
                s[idx] = _deal(str, math_end)
            s = math_begin.join(s)
        return s

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
            (ur'\style{font-family:Times New Roman}{g}', ur'\textsl{g}')
        ]
        for uni, latex in unicode2latex:
            s = s.replace(uni, latex)
        return s
    ori = unicode_2_latex(ori)
    ori = re.sub(ur'(?<!\\)%', '\%', ori)
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


def get_img(opt, img_width):
    opt = punc_in_img(opt)
    opt_imgs = re.findall(img_file_re, opt)
    if opt_imgs:
        for img_file in opt_imgs:
            if not os.path.isfile('{}{}'.format(img_path, img_file)):
                img_f = open('{}{}'.format(img_path, img_file), 'wb')
                img_f.write(urllib2.urlopen(
                    '{}{}'.format(img_url, img_file)).read())
            opt += '\\begin{{center}}\\includegraphics[width={}\\textwidth]{{{}{}}}\\end{{center}} '.format(
                img_width, img_path, img_file)
    opt = re.sub(img_re2, '', opt)
    return opt


def item_render(item_id):
    item = db.items.find_one({'_id': item_id})
    qss = ''
#================================================选择题=======================================    
    if item['data']['type'] in [1001, 2001]:
        desc = '\\fbox{\n \\begin{varwidth}{\\textwidth} \n %s' % item['data']['qs'][0]['desc']
        desc = desc.replace('[[nn]]', '\\dq ')
        opts = item['data']['qs'][0]['opts']
        opt_tex = get_opts_head(opts)

        for opt in opts:
            opt = get_img(opt, 0.222)
            opt_tex += '{%s}' % opt
        opt_tex += '\n \\end{varwidth} \n }\\\\'
#================================================填空题=======================================   
    elif item['data']['type'] in [1002, 2002]:
        desc = '\\fbox{\n \\begin{varwidth}{\\textwidth} \n %s' % item['data']['qs'][0]['desc']
        desc = desc.replace('[[nn]]', '\\dd ')
        opt_tex = '\\end{varwidth} \n }\\\\'
#================================================解答题=======================================   
    elif item['data']['type'] in [1003, 2003, 2004, 2005]:        
        if len(item['data']['stem']) == 0:
            if len(item['data']['qs']) == 1:
                desc = u'\\fbox{\n  \\begin{varwidth}{\\textwidth} \n %s \n ' % item['data']['qs'][0]['desc']
                desc = desc.replace('[[nn]]', '\\dd ')
                qss += u'\\end{varwidth} \n }\\\\'
            else:
                desc = ''
                qss += '\\begin{enumerate*} \n'
                for z in range(len(item['data']['qs'])):
                    qs = u'\\item[\\wqq] %s \n' %  item['data']['qs'][z]['desc']
                    qs = qs.replace('[[nn]]', '\\dd ')
                    qss += qs
                qss += '\\end{enumerate*} \n \\end{varwidth} \n }\\\\'
        else:
            desc = u'\\fbox{\n  \\begin{varwidth}{\\textwidth} \n %s' % item['data']['stem']
            if (len(item['data']['qs']) == 1) and (len(item['data']['qs'][0]['desc']) == 0):
                desc = desc.replace('[[nn]]', '\\dd ')
                qss += u'\\end{varwidth} \n }\\\\'
#================================================没有将环境终止字段加入qss而是加入desc中 待验证结果=======                
            else:
                qss = '\\begin{enumerate*} \n'
                for z in range(len(item['data']['qs'])):
                    if len(item['data']['qs'][z]['desc']) != 0:
                        qs = u'\\item[\\wqq] %s \n' %  item['data']['qs'][z]['desc']
                        qs = qs.replace('[[nn]]', '\\dd ')
                        qss += qs
                qss += '\\end{enumerate*} \n \\end{varwidth} \n }\\\\'
        opt_tex = ''



        # for z in range(len(item['data']['qs'])):
        #     if len(item['data']['qs'][z]['desc']) != 0:
        #         qs = u'\\begin{subquestion} %s \\end{subquestion}\n ' % item[
        #             'data']['qs'][z]['desc']
        #         qs = qs.replace('[[nn]]', '\\dd ')
                # qss += qs
    desc = get_img(desc, 0.5)
    qss = re.sub(img_re2, u'\\ ', qss)
    desc = str2latex(desc)
    qss = str2latex(qss)
    opt_tex = str2latex(opt_tex)
    if len(qss) == 0:
        item_tex = u'%{}\n{}\n\n{}'.format(
        item_id, desc,  opt_tex)
    else:
        item_tex = u'%{}\n{} \n {}\n{}'.format(
        item_id, desc, qss, opt_tex)

    
    return item_tex


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

paper_id = ObjectId("570f3c93e694aa11865683ff")
paper = db.papers.find_one({'_id': paper_id})
paper_path = '../papers/'
item_path = '../items/'
img_path = '../imgs/'
img_re2 = re.compile(ur'\[\[img\]\].*?\[\[/img\]\]')
img_file_re = re.compile(ur'\w+\.(?:png|jpg|gif|bmp)')

if os.path.exists(img_path):
    pass
else:
    os.makedirs(img_path)
if os.path.exists(paper_path):
    pass
else:
    os.makedirs(paper_path)


f = open(u'{path}{name}.tex'.format(path=paper_path, name=paper['name']), 'w')
f.write(physics_paper_render(paper))
f.close()
