const assert = require('node:assert/strict');
const {test} = require('node:test');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../../src/markeitech/dashboard/static');
const bars = (start, end) => Array.from({length:end-start}, (_,i)=>({time:(start+i)*3600,open:'1',high:'2',low:'0',close:'1',status:'COMPLETE'}));
function harness() {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {textContent:'',value:'',style:{},handlers:{},
      setAttribute(){},querySelectorAll(){return [];},querySelector(){return element(id+' child');},
      addEventListener(name,fn){this.handlers[name]=fn;},parentElement:{setAttribute(){}}});
    return elements.get(id);
  };
  let range={from:0,to:99}, data=[], callback;
  const scale={getVisibleLogicalRange:()=>range,setVisibleLogicalRange:r=>{range=r;},
    fitContent:()=>{range={from:0,to:data.length-1};},scrollToRealTime(){},
    subscribeVisibleLogicalRangeChange:fn=>{callback=fn;}};
  const series={setData:bars=>{data=bars;},applyOptions(){}};
  const requests=[];
  const context=vm.createContext({document:{getElementById:element},localStorage:{getItem:()=>null},
    window:{addEventListener(){}},setInterval(){},setTimeout,requestAnimationFrame:fn=>fn(),
    Date,console,LightweightCharts:{createChart:()=>({addSeries:()=>series,timeScale:()=>scale,subscribeCrosshairMove(){}})},
    fetch:async (url,options)=>{const body=JSON.parse(options.body);requests.push(body);return {ok:true,json:async()=>({status:'COMPLETED',candles:bars(body.start/3600,body.end/3600)})};}});
  vm.runInContext(readFileSync(path.join(root,'chart-window.js'),'utf8'),context);
  let source=readFileSync(path.join(root,'dashboard.js'),'utf8');
  source=source.replace('  select(rememberedInstrument);', `
    selected="ESZ6.CME";timeframe="1h";timeframeSeconds=3600;
    globalThis.api={installCandles,loadHistory,navigateHistory,restoreLive,follow,retainRecent,
      seed(bars){candles=bars;historyCandles=new Map(bars.map(b=>[b.time,b]));oldestCursor=bars[0].time;newestCursor=bars.at(-1).time+3600;following=false;},
      live(bars){liveCandles=new Map(bars.map(b=>[b.time,b]));},
      state(){return {candles,recentSize:recentCandles.size,historySize:historyCandles.size,oldestCursor,newestCursor,following,historyBusy,timeframe};}
    };`);
  vm.runInContext(source,context);
  return {api:context.api,context,element,requests,setRange:r=>{range=r;},range:()=>range,
    scroll:r=>{range=r;element('chart').handlers.wheel();callback(r);}};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
test('older pages preserve visible candle timestamps and fractional screen positions at capacity',async()=>{
  const h=harness();h.api.seed(bars(1000,1720));
  for(let n=0;n<5;n++) {
    h.setRange({from:10.25,to:99.25});
    const before=h.api.state().candles[10].time;
    const end=h.api.state().oldestCursor;
    await h.api.loadHistory(end-200*3600,end);
    const s=h.api.state();
    assert.equal(s.candles.length,720);assert.ok(s.historySize<=720);
    assert.equal(s.candles[Math.floor(h.range().from)].time,before);
    assert.equal(h.range().from%1,.25);assert.equal(h.range().to-h.range().from,89);
    assert.equal(s.candles[0].time,end-200*3600);
    h.api.live(bars(5000,5100));h.api.installCandles();
    assert.equal(h.api.state().candles[Math.floor(h.range().from)].time,before);
  }
});
test('newer pages refetch evicted candles and preserve the visible right-side anchor',async()=>{
  const h=harness();h.api.seed(bars(1000,1720));h.setRange({from:10,to:99});
  await h.api.loadHistory(800*3600,1000*3600);
  assert.equal(h.api.state().newestCursor,1520*3600);
  h.setRange({from:620.5,to:719.5});const anchor=h.api.state().candles[620].time;
  h.api.navigateHistory('newer');await settle();
  assert.equal(h.requests.at(-1).start,1520*3600);
  assert.equal(h.api.state().candles.at(-1).time,1719*3600);
  assert.equal(h.api.state().candles[Math.floor(h.range().from)].time,anchor);
  assert.equal(h.range().from%1,.5);
});
test('full visible capacity does not evict visible candles or issue a wasted request',()=>{
  const h=harness();h.api.seed(bars(1000,1720));h.setRange({from:0,to:719});
  h.api.navigateHistory('older');assert.equal(h.requests.length,0);
  assert.match(h.element('history-status').textContent,/Zoom in/);
});
test('empty market windows advance the cursor without shifting the visible candles',async()=>{
  const h=harness();h.api.seed(bars(1000,1100));h.setRange({from:10.5,to:70.5});
  h.context.fetch=async()=>({ok:true,json:async()=>({status:'COMPLETED',candles:[]})});
  await h.api.loadHistory(800*3600,1000*3600);
  assert.equal(h.api.state().oldestCursor,800*3600);
  assert.equal(h.api.state().candles[0].time,1000*3600);assert.equal(h.range().from,10.5);
});
test('Follow live restores recent history and ignores an obsolete in-flight older page',async()=>{
  const h=harness();h.api.seed(bars(1000,1720));h.setRange({from:10,to:99});
  const end=Math.floor(Date.now()/3600000);h.api.live(bars(end,end+1));
  let release;
  h.context.fetch=async(url,options)=>{
    const body=JSON.parse(options.body);h.requests.push(body);
    if(body.end===1000*3600)await new Promise(resolve=>{release=resolve;});
    return {ok:true,json:async()=>({status:'COMPLETED',candles:bars(body.start/3600,body.end/3600)})};
  };
  const old=h.api.loadHistory(800*3600,1000*3600);
  await h.api.restoreLive();release();await old;
  const s=h.api.state();assert.equal(s.following,true);assert.equal(s.timeframe,'1h');
  assert.equal(s.candles[0].time,(end-200)*3600);assert.equal(s.candles.at(-1).time,end*3600);
  assert.equal(s.candles.length,201);assert.equal(s.historyBusy,false);
});
test('scrolling near the newer edge requests forward history',async()=>{
  const h=harness();h.api.seed(bars(1000,1720));
  h.scroll({from:600,to:719});await settle();
  assert.equal(h.requests.at(-1).start,1720*3600);
  assert.equal(h.requests.at(-1).timeframe,'1h');
});
test('explicit date range replaces old browsing data and stays bounded',async()=>{
  const h=harness();h.api.seed(bars(1000,1720));
  await h.api.loadHistory(2000*3600,2200*3600,true);
  assert.equal(h.api.state().candles.length,200);
  assert.equal(h.api.state().candles[0].time,2000*3600);
});
test('offset provider timestamps keep aligned request bounds with overlap rather than gaps',async()=>{
  const h=harness();const shifted=bars(1000,1720).map(b=>({...b,time:b.time+1800}));
  h.api.seed(shifted);h.setRange({from:10,to:99});h.api.navigateHistory('older');await settle();
  assert.equal(h.requests[0].end,1001*3600);
  assert.equal(h.requests[0].start%3600,0);
  h.setRange({from:620,to:719});const firstEvicted=h.api.state().newestCursor;
  h.api.navigateHistory('newer');await settle();
  assert.equal(h.requests.at(-1).start,Math.floor(firstEvicted/3600)*3600);
});
test('paging away from a full protected far edge does not repeatedly request discarded data',()=>{
  const h=harness();h.api.seed(bars(1000,1720));h.setRange({from:620,to:719});
  h.api.navigateHistory('older');assert.equal(h.requests.length,0);
  assert.match(h.element('history-status').textContent,/pan/);
});
test('Follow live keeps the browsing chart visible until recent history arrives',async()=>{
  const h=harness();h.api.seed(bars(1000,1720));h.setRange({from:20.25,to:119.25});
  const end=Math.floor(Date.now()/3600000);h.api.live(bars(end,end+1));
  let release;
  h.context.fetch=async()=>{
    await new Promise(resolve=>{release=resolve;});
    return {ok:true,json:async()=>({status:'COMPLETED',candles:bars(end-200,end)})};
  };
  const restore=h.api.restoreLive();
  h.api.installCandles(); // Native updates continue while history is pending.
  assert.equal(h.api.state().candles.length,720);
  assert.equal(h.api.state().candles[0].time,1000*3600);
  assert.equal(h.range().from,20.25);assert.equal(h.api.state().following,false);
  release();await restore;
  assert.equal(h.api.state().following,true);
  assert.equal(h.api.state().candles.length,201);
  assert.equal(h.api.state().candles[0].time,(end-200)*3600);
});
test('failed Follow live history preserves the existing chart and exposes failure',async()=>{
  const h=harness();h.api.seed(bars(1000,1720));h.setRange({from:20.25,to:119.25});
  h.context.fetch=async()=>{throw new Error('History unavailable');};
  await h.api.restoreLive();
  assert.equal(h.api.state().candles.length,720);
  assert.equal(h.api.state().candles[0].time,1000*3600);
  assert.equal(h.range().from,20.25);assert.equal(h.api.state().following,false);
  assert.equal(h.api.state().historyBusy,false);
  assert.match(h.element('history-status').textContent,/History unavailable/);
});
test('Follow live restores already-loaded recent history synchronously without another request',async()=>{
  const h=harness();const end=Math.floor(Date.now()/3600000);
  h.api.follow(true);h.api.live(bars(end,end+1));
  await h.api.loadHistory((end-200)*3600,end*3600,false,true);
  const requests=h.requests.length;
  h.api.seed(bars(1000,1720));h.setRange({from:20,to:119});
  // The live tail advances while the operator browses an older window.
  h.api.live(bars(end,end+2));
  const restore=h.api.restoreLive();
  assert.equal(h.api.state().following,true); // Before awaiting anything.
  assert.equal(h.api.state().candles[0].time,(end-200)*3600);
  assert.equal(h.api.state().candles.at(-1).time,(end+1)*3600);
  assert.equal(h.requests.length,requests);
  await restore;
  assert.equal(h.requests.length,requests);
});
test('cached Follow live supersedes a pending Older request immediately',async()=>{
  const h=harness();const end=Math.floor(Date.now()/3600000);
  h.api.follow(true);h.api.live(bars(end,end+1));
  await h.api.loadHistory((end-200)*3600,end*3600,false,true);
  h.api.seed(bars(1000,1720));h.setRange({from:20,to:119});
  let release;
  h.context.fetch=async()=>{await new Promise(resolve=>{release=resolve;});return {ok:true,json:async()=>({status:'COMPLETED',candles:bars(800,1000)})};};
  const pending=h.api.loadHistory(800*3600,1000*3600);
  h.api.restoreLive();
  assert.equal(h.api.state().following,true);assert.equal(h.api.state().historyBusy,false);
  assert.equal(h.api.state().candles[0].time,(end-200)*3600);
  release();await pending;
  assert.equal(h.api.state().candles[0].time,(end-200)*3600);
});
test('recent cache includes fetched pages and stays bounded as native bars advance',async()=>{
  const h=harness();const end=Math.floor(Date.now()/3600000);
  h.api.follow(true);h.api.live(bars(end,end+1));
  await h.api.loadHistory((end-200)*3600,end*3600,false,true);
  h.setRange({from:0,to:50});
  await h.api.loadHistory((end-400)*3600,(end-200)*3600);
  h.api.restoreLive();
  assert.equal(h.api.state().candles[0].time,(end-400)*3600);
  h.api.follow(false);
  h.api.retainRecent(bars(end,end+1000));
  assert.equal(h.api.state().recentSize,720);
  const count=h.requests.length;
  h.api.restoreLive();
  assert.equal(h.api.state().candles.length,720);
  assert.equal(h.api.state().candles.at(-1).time,(end+999)*3600);
  assert.equal(h.requests.length,count);
});
