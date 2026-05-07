from __future__ import annotations

import asyncio
import httpx
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

router = APIRouter()

_SEARCH_URL   = "https://search.rcsb.org/rcsbsearch/v2/query"
_ENTRY_URL    = "https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
_PDB_FILE_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"


async def _fetch_titles(pdb_ids: list[str]) -> dict[str, str]:
    titles: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for pdb_id in pdb_ids:
            try:
                r = await client.get(_ENTRY_URL.format(pdb_id=pdb_id))
                titles[pdb_id] = r.json().get("struct", {}).get("title", pdb_id) if r.status_code == 200 else pdb_id
            except Exception:
                titles[pdb_id] = pdb_id
    return titles


@router.get("/pdb/search")
async def search_pdb(query: str = Query(..., min_length=1)) -> dict:
    search_body = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {
                "value": query
            }
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {
                "start": 0,
                "rows": 5
            }
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://search.rcsb.org/rcsbsearch/v2/query",
            json=search_body,
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )
        resp.raise_for_status()
        data = resp.json()

        pdb_ids = [
            hit.get("identifier", "")
            for hit in data.get("result_set", [])
            if hit.get("identifier")
        ]

        async def fetch_title(pid: str) -> str:
            try:
                r = await client.get(_ENTRY_URL.format(pdb_id=pid), timeout=5.0)
                if r.status_code == 200:
                    return r.json().get("struct", {}).get("title", pid)
            except Exception:
                pass
            return pid

        titles = await asyncio.gather(*[fetch_title(pid) for pid in pdb_ids])

    return {
        "results": [
            {"pdb_id": pid, "title": title}
            for pid, title in zip(pdb_ids, titles)
        ]
    }


@router.get("/pdb/sequence-search")
async def sequence_search_pdb(sequence: str = Query(..., min_length=4)) -> dict:
    payload = {
        "query": {
            "type": "terminal",
            "service": "sequence",
            "parameters": {
                "evalue_cutoff": 1,
                "identity_cutoff": 0.7,
                "sequence_type": "protein",
                "value": sequence,
            },
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": 5},
        },
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(_SEARCH_URL, json=payload)
        if resp.status_code == 204:
            return {"results": []}
        resp.raise_for_status()
        hits = resp.json().get("result_set") or []

    pdb_ids = [h["identifier"] for h in hits]
    titles  = await _fetch_titles(pdb_ids)
    return {"results": [{"id": pid, "title": titles.get(pid, pid)} for pid in pdb_ids]}


@router.get("/pdb/fetch/{pdb_id}", response_class=PlainTextResponse)
async def fetch_pdb(pdb_id: str) -> PlainTextResponse:
    async with httpx.AsyncClient() as client:
        url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
        resp = await client.get(url, timeout=30.0)

        if resp.status_code != 200:
            url = f"https://www.rcsb.org/download/{pdb_id.upper()}.pdb"
            resp = await client.get(url, timeout=30.0)

        resp.raise_for_status()

    return PlainTextResponse(content=resp.text, media_type="text/plain")
