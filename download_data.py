"""Download the three category archives linked by the official MVTec AD page."""
import argparse
import json
from pathlib import Path
import tarfile
import urllib.request

from study.io import sha256, write_json


URLS = {
    'screw': 'https://www.mydrive.ch/shares/163649/cfd394b4e3a49013745fab9e2084988a/download/420938130-1629960389/screw.tar.xz',
    'capsule': 'https://www.mydrive.ch/shares/163642/236d4304eaf9526b350b18807789ce86/download/420937454-1629958872/capsule.tar.xz',
    'metal_nut': 'https://www.mydrive.ch/shares/163647/6d5a833cdee9035a45d5ce0921ecd24d/download/420937637-1629959294/metal_nut.tar.xz',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--categories', nargs='+', choices=URLS, default=list(URLS))
    parser.add_argument('--data', type=Path, default=Path('data/mvtec'))
    parser.add_argument('--archives', type=Path, default=Path('data/archives'))
    args = parser.parse_args()
    args.data.mkdir(parents=True, exist_ok=True)
    args.archives.mkdir(parents=True, exist_ok=True)
    for category in args.categories:
        archive = args.archives / f'{category}.tar.xz'
        manifest = args.data / f'{category}_download.json'
        if manifest.exists() and (args.data / category / 'train/good').is_dir():
            print(f'{category}: already extracted; delete its download manifest to re-extract.', flush=True)
            continue
        if not archive.exists():
            partial = archive.with_suffix('.xz.part')
            print(f'Downloading {category} from the MVTec official download link...', flush=True)
            request = urllib.request.Request(URLS[category], headers={'User-Agent': 'Group6-PatchCore-Study/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as f:
                while chunk := response.read(4 * 1024 * 1024):
                    f.write(chunk)
            partial.replace(archive)
        # Do not extract unexpected paths or symbolic/hard links from an archive.
        with tarfile.open(archive, 'r:xz') as tar:
            members = tar.getmembers()
            for member in members:
                p = Path(member.name)
                if p.is_absolute() or '..' in p.parts or not (member.isfile() or member.isdir()):
                    raise ValueError(f'Unsafe archive member: {member.name}')
            roots = {Path(m.name).parts[0] for m in members if Path(m.name).parts}
            destination = args.data if category in roots else args.data / category
            destination.mkdir(parents=True, exist_ok=True)
            tar.extractall(destination, members=members, filter='data')
        write_json(manifest, {
            'category': category, 'source_url': URLS[category],
            'source_page': 'https://www.mvtec.com/research-teaching/datasets/mvtec-ad/downloads',
            'archive_sha256': sha256(archive), 'checksum_status': 'Locally computed; no official checksum compared.',
            'license': 'CC BY-NC-SA 4.0',
        })
        print(f'{category}: ready at {args.data / category}', flush=True)


if __name__ == '__main__':
    main()
