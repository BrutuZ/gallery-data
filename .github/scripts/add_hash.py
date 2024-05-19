#! /usr/bin/python
from argparse import ArgumentParser
from os import environ as env
from requests import get
import json

args = ArgumentParser()
args.add_argument('--id', action='append', type=int)
args.add_argument('--key', action='append')
args.add_argument('--hash', action='append')
args.add_argument('--issues', action='store_true')
args.add_argument('--minify', action='store_true')
args = args.parse_args()


def parse_body(body: str) -> dict:
    return json.loads(body.replace('```', '').replace('json', '').strip())


if args.issues:
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }

    query = {'state': 'open', 'per-page': 100}
    issue_list = get(
        f'https://api.github.com/repos/{env["GITHUB_REPOSITORY"]}/issues',
        params=query,
        headers=headers,
    ).json()
    params: list[tuple[int, str, str]] = [
        tuple(parse_body(issue['body']).values()) for issue in issue_list
    ]
else:
    params: list[tuple[int, str, str]] = map(
        lambda i, k, h: (i, k, h), args.id, args.key, args.hash
    )


with open('galleries.json', encoding='utf-8') as file:
    # galleries = file.readlines()
    parsed_galleries = json.loads(file.read())
    print('Parsed galleries.json file with', len(parsed_galleries), 'entries')

with open('keys.json', 'rt', encoding='utf-8') as file:
    parsed_keys = json.loads(file.read())
    print('Parsed keys.json file with', len(parsed_keys), 'entries')


def search_entry(id: int, key: str, hash: str) -> dict:
    start, end = None, None
    for index, line in enumerate(parsed_galleries):
        if f'"gid": {id},' in line:
            start = index - 2
            print(f'{start=}')
        # if '"hash": null,' in strline and found:
        if start and line.startswith("  },"):
            end = index + 1
            print(f'{end=}')
            break
            # lines[index] = strline.replace(
            #     '"hash": null,', f'"hash": "{hash}",'
            # )
        continue

    if not start and not end:
        raise EOFError()
    entry = json.loads("".join(parsed_galleries[start:end]).strip(',\n'))
    # lines = None
    # file.seek(0)
    # file.writelines(lines)
    # print('Wrote file')

    minentry = {
        'id': id,
        'key': key,
        'hash': hash,
        'url': entry['url'],
        'names': [i['name'] for i in entry['images']],
    }

    key_index = [
        index for index, data in enumerate(parsed_keys) if data['id'] == id
    ][0]
    print(key_index)
    print(parsed_keys[key_index], '->', minentry)
    parsed_keys[key_index] = minentry
    return parsed_keys


def parse_entry(id: int, key: str, hash: str):
    gallery_index, gallery_entry = next(
        ((i, e) for i, e in enumerate(parsed_galleries) if id == e['gid']),
        (None, None),
    )
    key_index = next(
        (i for i, e in enumerate(parsed_keys) if e['id'] == id), None
    )
    if None in (gallery_index, gallery_entry, key_index):
        raise EOFError()

    if (
        gallery_entry.get('key') != key
        or gallery_entry.get('hash') != hash
    ):
        updated_gallery = {}
        for k, v in gallery_entry.items():
            updated_gallery[k] = v
            if k in ['gid', 'key']:
                updated_gallery['key'] = key
            if k in ['url', 'hash']:
                updated_gallery['hash'] = hash

        parsed_galleries[gallery_index] = updated_gallery

    key_entry = {
        'id': id,
        'key': key,
        'hash': hash,
        'url': gallery_entry['url'],
        'names': [i['name'] for i in gallery_entry['images']],
    }
    parsed_keys[key_index] = key_entry


print(f'Processing {len(params)} entries')
for id, key, hash in params:
    # parsed_keys = search_entry(id, key, hash)
    print(f'Now processing {id=}, {key=}, {hash=}')
    parse_entry(id, key, hash)


outputs = ['galleries']
if args.minify:
    outputs.extend(('keys.min', 'galleries.min'))
for jsonfile in outputs:
    with open(f'{jsonfile}.json', 'wt', encoding='utf-8') as file:
        # file.seek(0)
        file.write(
            json.dumps(
                parsed_keys if 'keys' in jsonfile else parsed_galleries,
                indent=0 if '.min' in jsonfile else 2,
                ensure_ascii=False,
            )
        )
        print(f'Wrote {jsonfile}.json')
