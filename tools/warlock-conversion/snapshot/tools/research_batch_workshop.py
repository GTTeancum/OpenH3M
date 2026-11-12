"""Cache public MCC Workshop search results; results are leads, not verified ports."""
import concurrent.futures
import json
from pathlib import Path
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[4]
QUERIES=('Desolation','High Noon','Penance','Breakneck','Reflection','Haven',
         'Sword Base','Forge Island','Erosion','Impact')


def search(query):
    work=ROOT/'work/map-conversion-batch/research'
    work.mkdir(exist_ok=True)
    path=work/(query.lower().replace(' ','-')+'-search.html')
    url='https://steamcommunity.com/workshop/browse/?'+urllib.parse.urlencode(
        dict(appid=976730,searchtext=query,browsesort='textsearch',section='items'))
    try:
        if not path.exists():path.write_bytes(urllib.request.urlopen(url,timeout=30).read())
        soup=BeautifulSoup(path.read_bytes(),'html.parser')
        found={a['href']:a.get_text(' ',strip=True) for a in soup.select('a[href*=filedetails]')
               if a.get_text(' ',strip=True)}
        return dict(query=query,url=url,first_page_only=True,
                    results=[dict(title=title,url=url) for url,title in found.items()])
    except Exception as exc:return dict(query=query,url=url,error=str(exc))


if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(search,QUERIES))
    (ROOT/'work/map-conversion-batch/workshop-search.json').write_text(json.dumps(results,indent=2)+'\n')
    for row in results:
        print(json.dumps(dict(query=row['query'],error=row.get('error'),
             matches=[r for r in row.get('results',[]) if row['query'].lower() in r['title'].lower()])))
