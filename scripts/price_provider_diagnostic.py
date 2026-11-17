"""Bounded live diagnostic of the existing provider. No quotes retained or logged."""
import json
import context

def main():
    for ticker in ("WWI.OL","WWIB.OL","ERIC-A.ST","ERIC-B.ST"):
        for window in ("1y","5d"):
            data=context._chart(ticker,rng=window)
            health=context.latest_bar_health(data)
            print("PRICE_DIAGNOSTIC "+json.dumps({"ticker":ticker,"window":window,**health}),flush=True)
if __name__=="__main__":main()
