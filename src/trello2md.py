#!/usr/bin/python3
# -*- coding: utf-8 -*-

""" 
Terminal program to convert Trello's json-exports to markdown.
Origin: https://github.com/phipsgabler/trello2md
Fork: https://github.com/pwab/trello2md
"""

import sys
import argparse
import json
import re


# an url in a line (obligatory starting with the protocol part)
find_url = re.compile('(^|.* )([a-zA-Z]{3,4}://[^ ]*)(.*)$')


def unlines(line):
    """Remove all newlines from a string."""

    return line.translate(str.maketrans('\n', ' '))


def prepare_content(content):
    """Prepare nested markdown in content of a card."""
    
    result = []
    for line in content.splitlines():
        # turn urls into actual links
        match = find_url.match(line)
        if match:
            line = '{0}[{1}]({1}){2}'.format(match.group(1), match.group(2), match.group(3))
           
        # correct trello's heading levels (add two)
        if line.startswith('#'):
            # TODO: String to config -> '##{0}'
            result.append('##{0}'.format(unlines(line)))
        else:
            result.append(line)
    
    return '\n'.join(result)


def prepare_all_comments(data):
    """Returns a dictionary for each card_id with a list of comments"""
    ret = {}
    
    for action in data['actions']:
        if action['type'] == 'commentCard':
            card_id = action['data']['card']['id']
            
            if card_id not in ret:
                ret[card_id] = []
               
            name = action['memberCreator']['fullName']
            date = action['date']
            content = prepare_content(action['data']['text'])

            # TODO: Better markdown support in comments (e.g. linebreaks)
            # TODO: String to config -> '**{name}** ({date}):\n{content} \n'
            comment_string = '**{name}**:\n\n{content}\n'.format(
                name=name, date=date, content=content)
            
            ret[card_id].append(comment_string)
    return ret


def print_card(card_id, data, comments, print_labels):
    """Print name, content, comments and attachments of a card."""

    # get card and pre-format content
    card = next(c for c in data['cards'] if c['id'] == card_id)
    content = prepare_content(card['desc']) + '\n'

    comment_output = ''
    # comments are empty if they should not be printed
    if card_id in comments:
        # TODO: String to config -> '### Comments\n'
        comment_output = '### Comments\n'
        # TODO: String to config -> '\n\n'
        comment_output += '\n\n'.join(comments[card_id])

    # format labels, if wanted
    labels = []
    if print_labels and card['labels']:
        # TODO: String to config -> '('
        labels.append('(')

        for n, label in enumerate(card['labels']):
            # TODO: String to config -> ', '
            separator = ', ' * bool(n)  # only for n > 0
            # TODO: String to config -> '{sep}_{lbl}_'
            label_string = '{sep}_{lbl}_'.format(
              lbl=(label['name'] or label['color']),
              sep=separator)
            labels.append(label_string)

        # TODO: String to config -> ') '
        labels.append(') ')
        
    labels_string = ''.join(labels)

    # format attachments
    links = ((unlines(attm['name']), attm['url']) for attm in card['attachments'])
    # TODO: String to config -> '[{0}]({1})'
    attachments = ('[{0}]({1})'.format(name, url) for name, url in links)
    attachments_string = '\n\n'.join(attachments) + '\n'

    # put it together
    # TODO: String to config -> '## {name} {lbls}\n{cntnt}\n{attms}\n{comments}\n'
    return '## {name} {lbls}\n{cntnt}\n{attms}\n{comments}\n'.format(
                                          name=unlines(card['name']),
                                          cntnt=content,
                                          attms=attachments_string,
                                          comments=comment_output,
                                          lbls=labels_string)


def print_checklists(card_id, data):
    """Print a checklist as subsection with itemize."""

    card = next(c for c in data['cards'] if c['id'] == card_id)

    result = []
    for cl_id in card['idChecklists']:
        checklist = next(cl for cl in data['checklists'] if cl['id'] == cl_id)
        items_string = '\n'.join('- [ ] ' + item['name'] for item in checklist['checkItems'])
        # TODO: String to config -> '### Checklist: {name}\n\n{items}'
        result.append('### {name}\n\n{items}'.format(name=checklist['name'],
                                                     items=items_string))

    result.append('\n\n')
    return '\n\n'.join(result)


def main():
    """Main entry point for trello2md."""
    parser = argparse.ArgumentParser(description='Convert a JSON export from Trello to Markdown.')
    parser.add_argument('inputfile', help='The input JSON file')
    parser.add_argument('-i', '--header', help='Include header page', action='store_true')
    parser.add_argument('-m', '--comments', help='Include card comments', action='store_true')
    parser.add_argument('-l', '--labels', help='Print card labels', action='store_true')
    parser.add_argument('-a', '--archived', help='Don\'t ignore archived lists', action='store_true')
    parser.add_argument('-c', '--card-links', help='(Currently not implemented)', action='store_true')
    parser.add_argument('-o', '--output', help='The output file to create')

    args = parser.parse_args()

    # load infile to 'data'
    try:
        with open(args.inputfile, 'r', encoding='utf8') as inf:
            data = json.load(inf)
    except IOError as e:
        sys.exit('I/O error({0}): {1}'.format(e.errno, e.strerror))
    
    markdown = []

    # optionally, include header page
    if args.header:
        markdown.append('**Board name: {0}**\n\n'.format(data['name']))
        markdown.append('Short URL: [{0}]({0})  \n'.format(data['shortUrl']))
        markdown.append('Number of lists: {0}  \n'.format(len(data['lists'])))
        markdown.append('Number of cards in lists: {0}  \n'.format(len(data['cards'])))
        markdown.append('Last change: {0}\n\n\n'.format(data['dateLastActivity']))

    comments = {}
    if args.comments:
        comments = prepare_all_comments(data)

    # process all lists in 'data', respecting closeness
    for lst in data['lists']:
        if not lst['closed'] or args.archived:
            # format list header
            # TODO: String to config -> '# {0}\n\n'
            markdown.append('# {0}\n\n'.format(unlines(lst['name'])))

            # process all cards in current list
            for card in data['cards']:
                if (not card['closed'] or args.archived) and (card['idList'] == lst['id']):
                    markdown.append(print_card(card['id'],
                                               data,
                                               comments,
                                               args.labels))
                    markdown.append(print_checklists(card['id'], data))

    # save result to file
    if args.output:
        outputfile = args.output
    else:
        outputfile = args.inputfile.replace('.json', '.md')
        if outputfile == args.inputfile:
            outputfile += '.md'

    try:
        with open(outputfile, 'w', encoding='utf8') as of:
            of.write(''.join(markdown))

        print('Successfully translated to "{0}"!'.format(outputfile))

        if args.card_links:
            print('Option --card-links is currently unimplemented and ignored.')

    except IOError as e:
        sys.exit('I/O error({0}): {1}'.format(e.errno, e.strerror))


if __name__ == '__main__':
    main()
