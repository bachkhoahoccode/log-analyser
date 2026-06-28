from random import randint, choice
from datetime import datetime, timedelta
from pathlib import Path

def main():
    outdir=Path('data/sample_datasets')
    outdir.mkdir(exist_ok=True)

    methods=["GET","POST","PUT","DELETE"]
    uris=["/","/index.html","/login","/admin","/api/users","/search?q=test","/images/logo.png","/download/file.zip"]
    statuses=[200,200,200,200,301,302,400,401,403,404,500]
    uas=["Mozilla/5.0","curl/8.0","python-requests/2.31","Go-http-client/1.1"]
    refs=["-","https://google.com/","https://example.com/","https://bing.com/"]

    start=datetime(2026,6,28,8,0,0)

    def ip():
        return ".".join(str(randint(1,254)) for _ in range(4))

    clf=[]
    combined=[]
    flex=[]

    for i in range(200):
        t=start+timedelta(seconds=i*17)
        method=choice(methods)
        uri=choice(uris)
        status=choice(statuses)
        size=randint(0,20000)
        proto="HTTP/1.1"
        clf.append(f'{ip()} - - [{t.strftime("%d/%b/%Y:%H:%M:%S +0700")}] "{method} {uri} {proto}" {status} {size}')
        combined.append(f'{ip()} - - [{t.strftime("%d/%b/%Y:%H:%M:%S +0700")}] "{method} {uri} {proto}" {status} {size} "{choice(refs)}" "{choice(uas)}"')
        flex.append(f'{ip()} - - [{t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}+0700] "{method} {uri} {proto}" {status} {size} "{choice(refs)}" "{choice(uas)}"')

    (outdir/"apache_clf_200.log").write_text("\n".join(clf))
    (outdir/"apache_combined_200.log").write_text("\n".join(combined))
    (outdir/"flexible_iso_ms_200.log").write_text("\n".join(flex))

    print(outdir)
if __name__ == "__main__":
    main()