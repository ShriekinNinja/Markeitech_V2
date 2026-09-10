"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const names = {ES:"E-mini S&P 500",NQ:"E-mini Nasdaq 100",CL:"WTI Crude Oil",SPY:"SPDR S&P 500 ETF",QQQ:"Invesco QQQ",SPX:"S&P 500 Index",VIX:"CBOE Volatility Index"};
  const rootSymbol = id => id.split(".")[0].replace(/^\^/, "").replace(/([A-Z]+)[FGHJKMNQUVXZ]\d+$/, "$1");
  const price = value => value == null ? "—" : Number(value).toLocaleString("en-US", {minimumFractionDigits: (String(value).split(".")[1] || "").length, maximumFractionDigits: 8});
  const utc = seconds => new Date(seconds * 1000).toISOString().slice(11, 19);
  const age = ns => ns == null ? "Awaiting data" : `${Math.max(0, Math.floor((Date.now() - Number(BigInt(ns) / 1000000n)) / 1000))}s ago`;
  const el = (tag, cls, text) => {const element = document.createElement(tag); element.className=cls; if(text != null) element.textContent=text; return element;};
  let selected = null, rows = [], candles = [], stream = null, generation = 0, following = true;
  const buttons = new Map();
  const chart = LightweightCharts.createChart($("chart"), {
    autoSize: true,
    layout: {background:{type:"solid",color:"#111111"},textColor:"#a9a9a9",fontFamily:"-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",fontSize:11,attributionLogo:true},
    grid: {vertLines:{color:"#252525",style:2},horzLines:{color:"#252525",style:2}},
    rightPriceScale: {borderColor:"#3b3b3b",scaleMargins:{top:0.1,bottom:0.1}},
    timeScale: {borderColor:"#3b3b3b",timeVisible:true,secondsVisible:true,rightOffset:6,barSpacing:8},
    crosshair: {vertLine:{color:"#827656",labelBackgroundColor:"#615238"},horzLine:{color:"#827656",labelBackgroundColor:"#615238"}},
    localization: {locale:"en-US",timeFormatter:utc}
  });
  const series = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor:"#eeeeee",downColor:"#c42b32",borderUpColor:"#eeeeee",borderDownColor:"#c42b32",
    wickUpColor:"#eeeeee",wickDownColor:"#c42b32",lastValueVisible:false,priceLineVisible:false,
  });
  let priceLine = null;
  const chartBar = bar => ({time:bar.time,open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close)});
  function setConnected(value, label) {
    $("connection").textContent=label || (value?"Connected to system":"Disconnected · reconnecting");
    $("connection-dot").style.background=value?"#d1ad60":"#747474";
  }
  function follow(value) {following=value; $("follow").setAttribute("aria-pressed",String(value)); if(value) chart.timeScale().scrollToRealTime();}
  $("follow").addEventListener("click",()=>follow(!following));
  $("fit").addEventListener("click",()=>{follow(false);chart.timeScale().fitContent();});
  $("chart").addEventListener("pointerdown",()=>follow(false));
  $("chart").addEventListener("wheel",()=>follow(false),{passive:true});
  function legend(bar) {
    $("ohlc").textContent=bar?`O ${price(bar.open)}    H ${price(bar.high)}    L ${price(bar.low)}    C ${price(bar.close)}`:"Waiting for completed provider candles";
  }
  chart.subscribeCrosshairMove(param => legend(param.seriesData.get(series) || candles.at(-1)));
  function renderRows() {
    const ids = new Set(rows.map(row=>row.instrument_id));
    for(const [id,entry] of buttons) if(!ids.has(id)){entry.button.remove();buttons.delete(id);}
    for(const row of rows) {
      const id=row.instrument_id;
      if(!buttons.has(id)) {
        const button=el("button","instrument-row"); button.type="button";
        const symbol=el("span","row-symbol",rootSymbol(id)), value=el("span","row-price"), identity=el("span","row-id",id), source=el("span","row-source","5s close");
        const status=el("span","row-status"), ageLabel=el("span","");status.append(el("i",""),ageLabel);
        button.append(symbol,value,identity,source,status);
        button.addEventListener("click",()=>select(id));$("watchlist").append(button);
        buttons.set(id,{button,value,ageLabel});
      }
      const entry=buttons.get(id);entry.value.textContent=price(row.last);
      entry.button.classList.toggle("selected",id===selected);entry.button.setAttribute("aria-pressed",String(id===selected));
      entry.button.setAttribute("aria-label",`${id}, latest ${price(row.last)}`);
    }
    filter(); ages();
  }
  function filter() {
    const search=$("search").value.trim().toLowerCase();let count=0;
    for(const [id,entry] of buttons){entry.button.hidden=!id.toLowerCase().includes(search);if(!entry.button.hidden)count++;}
    $("empty-watchlist").hidden=count>0;
    $("empty-watchlist").textContent=rows.length?"No matching instruments":"No enabled instruments";
  }
  $("search").addEventListener("input",filter);
  function ages() {
    $("clock").textContent=`UTC ${utc(Date.now()/1000)}`;
    for(const row of rows) {
      const states=Object.values(row.feed_states);
      const problem=states.find(s=>["FAILED","REJECTED","EXPIRED","CANCELED"].includes(s));
      buttons.get(row.instrument_id).ageLabel.textContent=problem?`Feed ${problem.toLowerCase()}`:age(row.bar_ts_event_ns || row.quote_ts_event_ns);
    }
    const row=rows.find(r=>r.instrument_id===selected);
    if(row){$("quote-age").textContent=row.capabilities.includes("top_of_book")?age(row.quote_ts_event_ns):"Not configured";$("bar-age").textContent=age(row.bar_ts_event_ns);}
  }
  setInterval(ages,1000);
  function render(view, reset) {
    selected=view.selected; rows=view.instruments;renderRows();
    const row=rows.find(r=>r.instrument_id===selected);
    const symbol=selected?rootSymbol(selected):"—";
    $("symbol").textContent=symbol;$("instrument-name").textContent=names[symbol] || "Market instrument";
    $("instrument-id").textContent=selected || "Watchlist is empty";
    $("last").textContent=price(row?.last);$("bid").textContent=price(row?.bid);$("ask").textContent=price(row?.ask);
    $("bar-time").textContent=row?.bar_ts_event_ns?`${utc(Number(BigInt(row.bar_ts_event_ns)/1000000000n))} UTC`:"—";
    if(reset) {
      candles=view.candles;series.setData(candles.map(chartBar));chart.timeScale().fitContent();follow(true);
    } else {
      for(const bar of view.candles){if(!candles.length || bar.time>candles.at(-1).time){candles.push(bar);series.update(chartBar(bar));}}
      const before=candles.length;
      candles=candles.filter(bar=>view.window_start==null || bar.time>=view.window_start).slice(-view.maximum_candles);
      if(before!==candles.length){const range=chart.timeScale().getVisibleLogicalRange();series.setData(candles.map(chartBar));if(!following && range)chart.timeScale().setVisibleLogicalRange({from:range.from-(before-candles.length),to:range.to-(before-candles.length)});}
      if(following)chart.timeScale().scrollToRealTime();
    }
    if(candles.length){
      const last=candles.at(-1);const precision=(last.close.split(".")[1]||"").length;
      series.applyOptions({priceFormat:{type:"price",precision,minMove:10**(-precision)}});
      const opts={price:Number(last.close),color:"#d1ad60",lineWidth:1,lineStyle:2,axisLabelVisible:true,title:""};
      if(priceLine)priceLine.applyOptions(opts);else priceLine=series.createPriceLine(opts);
    }else if(priceLine){series.removePriceLine(priceLine);priceLine=null;}
    $("chart-empty").hidden=candles.length>0;
    const configured=row?.capabilities.includes("watchlist_last");
    $("chart-empty").querySelector("h3").textContent=!selected?"No instrument selected":configured?"Waiting for candles":"Bar feed not configured";
    $("chart-empty").querySelector("p").textContent=configured?"The chart fills as five-second provider bars arrive.":"Select a watchlist instrument with a bar feed.";
    $("source").textContent=`IB · Requested ${view.requested_market_data_type} · Received mode unknown · UTC`;
    $("window-status").textContent=`${candles.length} candles · Current runtime session`;
    if(view.preview){$("source").textContent="OFFLINE PREVIEW · Synthetic data · UTC";setConnected(true,"Offline preview");}
    legend(candles.at(-1));ages();
  }
  async function select(id) {
    const token=++generation;if(stream)stream.close();stream=null;
    selected=id;candles=[];series.setData([]);if(priceLine){series.removePriceLine(priceLine);priceLine=null;}
    $("chart-empty").hidden=false;$("chart-empty").querySelector("h3").textContent="Loading instrument…";
    setConnected(false,"Connecting…");
    const query=id?`?instrument_id=${encodeURIComponent(id)}`:"";
    try {
      const response=await fetch(`/api/snapshot${query}`);if(!response.ok)throw new Error("Snapshot unavailable");
      const view=await response.json();if(token!==generation)return;render(view,true);
      stream=new EventSource(`/api/events${query}`);
      stream.addEventListener("update",event=>{if(token!==generation)return;setConnected(true);const update=JSON.parse(event.data);render(update,update.reset);});
      stream.addEventListener("stopping",()=>{if(token!==generation)return;setConnected(false,"System stopped");});
      stream.onerror=()=>{if(token===generation)setConnected(false);};
    } catch {if(token===generation){setConnected(false,"Unavailable · retrying");setTimeout(()=>{if(token===generation)select(id);},2000);}}
  }
  window.addEventListener("pagehide",()=>stream?.close());
  select(null);
})();
