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
  let timeframe = "1m", timeframeSeconds = 60;
  let rememberedInstrument = null;
  try {
    const preference = JSON.parse(localStorage.getItem("markeitech.dashboard.selection.v1") || "null");
    if (preference && typeof preference.instrument === "string" && preference.instrument.length <= 128) rememberedInstrument = preference.instrument;
    if (["1m", "5m", "15m", "30m", "1h", "4h", "1d"].includes(preference?.timeframe)) timeframe = preference.timeframe;
  } catch { /* Storage is optional; malformed or unavailable preferences cannot block startup. */ }
  function rememberSelection() {
    try { localStorage.setItem("markeitech.dashboard.selection.v1", JSON.stringify({instrument:selected,timeframe})); } catch {}
  }
  const timeframeButtons = [...$("timeframes").querySelectorAll("button[data-timeframe]")];
  function renderTimeframes() {
    for (const button of timeframeButtons) button.setAttribute("aria-pressed", String(button.dataset.timeframe === timeframe));
  }
  for (const button of timeframeButtons) button.addEventListener("click", () => {
    if (timeframe === button.dataset.timeframe) return;
    timeframe = button.dataset.timeframe;
    renderTimeframes();
    select(selected);
  });
  renderTimeframes();
  const buttons = new Map();
  const chart = LightweightCharts.createChart($("chart"), {
    autoSize: true,
    layout: {background:{type:"solid",color:"#111111"},textColor:"#a9a9a9",fontFamily:"-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",fontSize:11,attributionLogo:true},
    grid: {vertLines:{color:"#252525",style:2},horzLines:{color:"#252525",style:2}},
    rightPriceScale: {borderColor:"#3b3b3b",scaleMargins:{top:0.1,bottom:0.1}},
    timeScale: {borderColor:"#3b3b3b",timeVisible:true,secondsVisible:false,rightOffset:6,barSpacing:8},
    crosshair: {vertLine:{color:"#827656",labelBackgroundColor:"#615238"},horzLine:{color:"#827656",labelBackgroundColor:"#615238"}},
    localization: {locale:"en-US",timeFormatter:seconds=>new Date(seconds*1000).toISOString().replace("T"," ").slice(0,19)+" UTC"}
  });
  const series = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor:"#eeeeee",downColor:"#c42b32",borderUpColor:"#eeeeee",borderDownColor:"#c42b32",
    wickUpColor:"#eeeeee",wickDownColor:"#c42b32",lastValueVisible:false,priceLineVisible:false,
  });
  let priceLine = null, liveCandles = new Map(), historyCandles = new Map();
  let recentCandles = new Map(), recentHistoryReady = false;
  let historyBusy = false, historyIntent = false, rangeMode = null, oldestCursor = null, newestCursor = null, historyEpoch = 0, historyResultState = "waiting";
  let maximumCandles = 720, pageCandles = 200, initialCandles = 200, historyTimeout = 120, historyRetryMs = 1000, installing = false;
  const datetimeValue = seconds => new Date(seconds*1000).toISOString().slice(0,16);
  const parseDatetime = value => Date.parse(`${value}:00Z`)/1000;
  const historyStatus = text => {$("history-status").textContent=text;};
  function installCandles(reset=false, direction="stay") {
    const before=candles, range=chart.timeScale().getVisibleLogicalRange();
    const merged=new Map(candles.map(bar=>[bar.time,bar]));
    for(const [time,bar] of historyCandles)merged.set(time,bar);
    for(const [time,bar] of liveCandles) {
      // Do not join an old browsing window to a distant live tail across evicted history.
      if(following || (oldestCursor===null && newestCursor===null)
        || (time >= oldestCursor && time < newestCursor))merged.set(time,bar);
    }
    const all=[...merged.values()].filter(bar=>!rangeMode || (bar.time>=rangeMode.start && bar.time<rangeMode.end)).sort((a,b)=>a.time-b.time);
    const retained=DashboardWindow.retain(all, reset?[]:before, reset?null:range, maximumCandles, following?"newer":direction);
    candles=following?all.slice(-maximumCandles):retained.bars;
    if(candles.length) {
      const first=candles[0].time, last=candles.at(-1).time;
      if(all[0].time<first)oldestCursor=first;
      if(all.at(-1).time>last)newestCursor=all.find(bar=>bar.time>last).time;
      historyCandles=new Map([...historyCandles].filter(([time])=>time>=first && time<=last));
    }
    installing=true;series.setData(candles.map(chartBar));
    if(reset)chart.timeScale().fitContent();
    else if(!following && retained.range)chart.timeScale().setVisibleLogicalRange(retained.range);
    if(following)chart.timeScale().scrollToRealTime();
    updateWindowStatus();
    requestAnimationFrame(()=>{installing=false;});
  }
  function retainRecent(bars) {
    for(const bar of bars)recentCandles.set(bar.time,bar);
    recentCandles=new Map([...recentCandles].sort((a,b)=>a[0]-b[0]).slice(-maximumCandles));
  }
  const currentHistory = (token, epoch) => token===generation && epoch===historyEpoch;
  async function historyPage(start,end,token,epoch) {
    const deadline=Date.now()+historyTimeout*1000;
    const body=JSON.stringify({instrument_id:selected,start,end,timeframe});
    let response;
    do {
      if(!currentHistory(token,epoch))return null;
      response=await fetch("/api/history",{method:"POST",headers:{"Content-Type":"application/json"},body});
      if(response.status!==429)break;
      if(Date.now()>=deadline)throw new Error("History is still busy; try again");
      historyStatus("Waiting for history…");
      await new Promise(resolve=>setTimeout(resolve,historyRetryMs));
    } while(currentHistory(token,epoch));
    if(!currentHistory(token,epoch))return null;
    if(!response.ok){const error=await response.json();throw new Error(error.detail || "History unavailable");}
    let result=await response.json();
    while(result.status==="PENDING" && currentHistory(token,epoch) && Date.now()<deadline){
      await new Promise(resolve=>setTimeout(resolve,500));
      if(!currentHistory(token,epoch))return null;
      response=await fetch(`/api/history/${encodeURIComponent(result.request_id)}`);
      if(!response.ok)throw new Error("History request expired; try again");
      result=await response.json();
    }
    if(!currentHistory(token,epoch))return null;
    if(result.status!=="COMPLETED")throw new Error(result.detail || `History ${result.status.toLowerCase()}; try again`);
    return result;
  }
  async function loadHistory(start,end,replaceRange=false,initial=false,direction="older",restore=false) {
    if(historyBusy || !selected)return;
    const token=generation, epoch=++historyEpoch;historyBusy=true;historyIntent=false;historyResultState="loading";
    $("older").disabled=true;$("newer").disabled=true;$("show-range").disabled=true;if(!initial)follow(false);
    if(replaceRange){rangeMode={start,end};historyCandles.clear();candles=[];oldestCursor=start;newestCursor=end;installCandles(true);}
    let cursor=end, count=0;
    const pending=restore?new Map():null;
    try {
      while(cursor>start && currentHistory(token,epoch)){
        const duration=pageCandles*timeframeSeconds;
        if(duration<timeframeSeconds)throw new Error("Configured history page is shorter than this timeframe");
        const pageStart=Math.max(start,cursor-duration);
        historyStatus("Loading history…");
        const result=await historyPage(pageStart,cursor,token,epoch);if(!result)return;
        if(recentHistoryReady)retainRecent(result.candles);
        for(const candle of result.candles)(pending || historyCandles).set(candle.time,candle);
        count+=result.candles.length;
        if(restore){cursor=pageStart;continue;}
        oldestCursor=Math.min(oldestCursor ?? pageStart,pageStart);
        newestCursor=Math.max(newestCursor ?? cursor,cursor);
        cursor=pageStart;
        installCandles(replaceRange || (initial && following),direction);$("chart-empty").hidden=candles.length>0;
      }
      if(!currentHistory(token,epoch))return;
      if(restore) {
        // Commit only after every recent-history page succeeds; preserve the old view on failure.
        historyCandles=pending;candles=[];rangeMode=null;oldestCursor=start;newestCursor=end;
        follow(true);installCandles(true);$("chart-empty").hidden=candles.length>0;
      }
      if(initial){recentHistoryReady=true;retainRecent(candles);}
      historyResultState="completed";updateWindowStatus();
      historyStatus(count?`${count} candles loaded · UTC`:"No bars returned for this window");
      legend(candles.at(-1));
    } catch(error) {if(currentHistory(token,epoch)){historyResultState="failed";updateWindowStatus();historyStatus(error.message);}}
    finally {if(currentHistory(token,epoch)){historyBusy=false;$("older").disabled=false;$("newer").disabled=false;$("show-range").disabled=false;}}
  }
  function navigateHistory(direction) {
    if(historyBusy)return;
    if(rangeMode){historyStatus("Use Follow live before paging outside a date range");return;}
    if(!candles.length)return;
    const count=Math.min(pageCandles,DashboardWindow.room(candles,chart.timeScale().getVisibleLogicalRange(),maximumCandles,direction));
    if(count<1){historyStatus("Zoom in or pan toward the requested history to make room without removing visible candles");return;}
    const now=Math.floor(Date.now()/1000/timeframeSeconds)*timeframeSeconds;
    const cursor=direction==="older" ? (oldestCursor ?? candles[0].time)
      : (newestCursor ?? candles.at(-1).time+timeframeSeconds);
    // Requests use UTC-aligned bounds; overlap off-grid provider opens rather than skip them.
    const edge=(direction==="older" ? Math.ceil(cursor/timeframeSeconds) : Math.floor(cursor/timeframeSeconds))*timeframeSeconds;
    const start=direction==="older" ? edge-count*timeframeSeconds : edge;
    const end=direction==="older" ? edge : Math.min(now,edge+count*timeframeSeconds);
    if(end<=start){historyStatus("At the latest completed candle; use Follow live");return;}
    void loadHistory(start,end,false,false,direction);
  }
  const older=()=>navigateHistory("older");
  const newer=()=>navigateHistory("newer");
  $("older").addEventListener("click",older);
  $("newer").addEventListener("click",newer);
  $("range-form").addEventListener("submit",event=>{
    event.preventDefault();const start=Math.floor(parseDatetime($("range-start").value)/timeframeSeconds)*timeframeSeconds,end=Math.floor(parseDatetime($("range-end").value)/timeframeSeconds)*timeframeSeconds;
    if(!Number.isFinite(start)||!Number.isFinite(end)||start<=0||end<=start){historyStatus("Choose a valid UTC start and end");return;}
    if(end>Math.floor(Date.now()/60000)*60){historyStatus("End must be a completed UTC minute");return;}
    if(end-start>maximumCandles*timeframeSeconds){historyStatus(`Choose at most ${maximumCandles} candles at ${timeframe}`);return;}
    $("range-start").value=datetimeValue(start);$("range-end").value=datetimeValue(end);
    loadHistory(start,end,true);
  });
  chart.timeScale().subscribeVisibleLogicalRangeChange(range=>{
    if(!range || !historyIntent || historyBusy || following || installing || rangeMode)return;
    if(range.from<8)older();
    else if(range.to>candles.length-8)newer();
  });
  const chartBar = bar => ({time:bar.time,open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close)});
  function setConnected(value, label) {
    $("connection").textContent=label || (value?"Connected to system":"Disconnected · reconnecting");
    $("connection-dot").style.background=value?"#d1ad60":"#747474";
  }
  function follow(value) {
    if(following && !value && candles.length) {
      oldestCursor=Math.min(oldestCursor ?? candles[0].time,candles[0].time);
      newestCursor=Math.max(newestCursor ?? 0,candles.at(-1).time+timeframeSeconds);
    }
    following=value; $("follow").setAttribute("aria-pressed",String(value)); if(value) chart.timeScale().scrollToRealTime();}
  async function restoreLive() {
    // Supersede pending browser history work without touching the native subscription.
    historyEpoch++;historyBusy=false;historyIntent=false;
    if(recentHistoryReady) {
      historyCandles=new Map(recentCandles);candles=[];rangeMode=null;
      oldestCursor=recentCandles.size?recentCandles.values().next().value.time:null;
      newestCursor=null;historyResultState="completed";
      follow(true);installCandles(true);legend(candles.at(-1));
      $("chart-empty").hidden=candles.length>0;
      $("older").disabled=false;$("newer").disabled=false;$("show-range").disabled=false;
      historyStatus("Recent candles restored · UTC");
      return;
    }
    const end=Math.floor(Date.now()/1000/timeframeSeconds)*timeframeSeconds;
    await loadHistory(end-initialCandles*timeframeSeconds,end,false,true,"newer",true);
  }
  $("follow").addEventListener("click",()=>{
    if(following)follow(false);else void restoreLive();
  });
  $("fit").addEventListener("click",()=>{follow(false);chart.timeScale().fitContent();});
  $("chart").addEventListener("pointerdown",()=>{historyIntent=true;follow(false);});
  $("chart").addEventListener("wheel",()=>{historyIntent=true;follow(false);},{passive:true});
  function legend(bar) {
    $("ohlc").textContent=bar?`O ${price(bar.open)}    H ${price(bar.high)}    L ${price(bar.low)}    C ${price(bar.close)}`:`Waiting for ${timeframe} candles`;
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
    historyRetryMs=view.history_retry_interval_ms || 1000;
    timeframe = view.timeframe || "1m"; timeframeSeconds=view.timeframe_seconds || 60;
    renderTimeframes(); rememberSelection();
    chart.applyOptions({timeScale:{secondsVisible:!view.timeframe}});
    const row=rows.find(r=>r.instrument_id===selected);
    const symbol=selected?rootSymbol(selected):"—";
    $("symbol").textContent=symbol;$("instrument-name").textContent=names[symbol] || "Market instrument";
    $("instrument-id").textContent=selected || "Watchlist is empty";
    $("last").textContent=price(row?.last);$("bid").textContent=price(row?.bid);$("ask").textContent=price(row?.ask);
    $("bar-time").textContent=row?.bar_ts_event_ns?`${utc(Number(BigInt(row.bar_ts_event_ns)/1000000000n))} UTC`:"—";
    maximumCandles=view.maximum_candles;pageCandles=view.history_page_candles || 200;initialCandles=Math.min(view.initial_history_candles || 200,maximumCandles);historyTimeout=view.history_timeout_seconds || 120;
    if(reset)liveCandles=new Map(view.candles.map(bar=>[bar.time,bar]));
    else for(const bar of view.candles)liveCandles.set(bar.time,bar);
    liveCandles=new Map([...liveCandles].sort((a,b)=>a[0]-b[0]).slice(-maximumCandles));
    if(recentHistoryReady)retainRecent(view.candles);
    installCandles(reset && !rangeMode && !historyCandles.size);
    if(candles.length){
      const last=candles.at(-1);const precision=(last.close.split(".")[1]||"").length;
      series.applyOptions({priceFormat:{type:"price",precision,minMove:10**(-precision)}});
      const opts={price:Number(last.close),color:"#d1ad60",lineWidth:1,lineStyle:2,axisLabelVisible:true,title:""};
      if(priceLine)priceLine.applyOptions(opts);else priceLine=series.createPriceLine(opts);
    }else if(priceLine){series.removePriceLine(priceLine);priceLine=null;}
    $("chart-empty").hidden=candles.length>0;
    const configured=row?.capabilities.includes("watchlist_last");
    $("chart-empty").querySelector("h3").textContent=!selected?"No instrument selected":configured?"Waiting for candles":"Bar feed not configured";
    $("chart-empty").querySelector("p").textContent=configured?`${timeframe} candles update directly from IB.`:"Select a watchlist instrument with a bar feed.";
    $("source").textContent=`IB · Requested ${view.requested_market_data_type} · Received mode unknown · UTC`;
    if(view.preview){$("source").textContent="OFFLINE PREVIEW · Synthetic data · UTC";setConnected(true,"Offline preview");}
    legend(candles.at(-1));ages();
  }
  function updateWindowStatus() {
    const incomplete=candles.filter(bar=>bar.status==="INCOMPLETE").length;
    const phase=candles.at(-1)?.status?.toLowerCase() || "waiting";
    $("window-status").textContent=`${candles.length} candles · ${phase} · History ${historyResultState}${incomplete?` · ${incomplete} incomplete`:""}`;
  }
  function initialLoading(loading) {
    $("chart-loading").hidden=!loading;
    $("chart-loading").parentElement.setAttribute("aria-busy",String(loading));
  }
  let initialHistoryGeneration = -1;
  async function ensureInitialHistory(view, token) {
    if(token!==generation || initialHistoryGeneration===token || !selected || view.preview
      || !rows.find(row=>row.instrument_id===selected)?.capabilities.includes("watchlist_last"))return;
    initialHistoryGeneration=token;initialLoading(true);
    try {
      const end=Math.floor(Date.now()/1000/timeframeSeconds)*timeframeSeconds;
      await loadHistory(end-initialCandles*timeframeSeconds,end,false,true);
    } finally {if(token===generation)initialLoading(false);}
  }
  async function select(id) {
    initialLoading(true);
    const token=++generation;if(stream)stream.close();stream=null;
    selected=id;historyResultState="waiting";candles=[];liveCandles.clear();historyCandles.clear();recentCandles.clear();recentHistoryReady=false;rangeMode=null;oldestCursor=null;newestCursor=null;historyEpoch++;historyBusy=false;historyIntent=false;following=true;$("follow").setAttribute("aria-pressed","true");$("older").disabled=false;$("newer").disabled=false;$("show-range").disabled=false;historyStatus("");series.setData([]);if(priceLine){series.removePriceLine(priceLine);priceLine=null;}
    $("chart-empty").hidden=false;$("chart-empty").querySelector("h3").textContent="Loading instrument…";
    setConnected(false,"Connecting…");
    const query=`?timeframe=${encodeURIComponent(timeframe)}${id?`&instrument_id=${encodeURIComponent(id)}`:""}`;
    try {
      const response=await fetch(`/api/snapshot${query}`);
      if(response.status===404 && id && token===generation){select(null);return;}
      if(!response.ok)throw new Error("Snapshot unavailable");
      const view=await response.json();if(token!==generation)return;render(view,true);
      stream=new EventSource(`/api/events${query}`);
      stream.addEventListener("update",event=>{if(token!==generation)return;setConnected(true);const update=JSON.parse(event.data);render(update,update.reset);void ensureInitialHistory(update,token);});
      stream.addEventListener("stopping",()=>{if(token!==generation)return;setConnected(false,"System stopped");});
      stream.onerror=()=>{if(token===generation)setConnected(false);};
      await ensureInitialHistory(view,token);
    } catch {if(token===generation){setConnected(false,"Unavailable · retrying");setTimeout(()=>{if(token===generation)select(id);},2000);}}
    finally {if(token===generation && initialHistoryGeneration!==token)initialLoading(false);}
  }
  window.addEventListener("pagehide",()=>stream?.close());
  const now=Math.floor(Date.now()/60000)*60;$("range-start").value=datetimeValue(now-3600);$("range-end").value=datetimeValue(now);
  select(rememberedInstrument);
})();
