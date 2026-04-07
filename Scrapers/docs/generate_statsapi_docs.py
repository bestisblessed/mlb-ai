#!/usr/bin/env python

from statsapi import endpoints

# Open a Markdown file for writing
with open("statsapi_endpoints.md", "w") as file:
    lbb = """
* """
    lb = """
    """

    for k, v in endpoints.ENDPOINTS.items():
        file.write(f"## Endpoint: `{k}`{lb}")
        file.write(f"### URL: `{v['url']}`{lb}")
        rp = [pk for pk, pv in v['path_params'].items() if pv['required'] and pk != 'ver']
        rq = [' + '.join(q) for q in v['required_params'] if len(q) > 0]
        rp.extend(rq)
        file.write(f"### Required Parameters{lb}* {lbb.join(rp) if len(rp) else '*None*'}{lb}")
        ap = list(v['path_params'].keys()) + (v['query_params'] if v['query_params'] != [[]] else [])
        file.write(f"### All Parameters{lb}* {lbb.join(ap)}{lb}")
        if v.get("note"):
            file.write(f"### Note{lb}{v['note']}{lb}")

        file.write(f"-----{lb}")