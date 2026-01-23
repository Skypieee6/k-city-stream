import threading, time, requests, json, os
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template_string, jsonify, Response

app = Flask(__name__)

# --- CONFIGURATION ---
TMDB_API_KEY = "4cc3094d9a8a8db22ee80b5a4be6dcf9"
CACHE_FILE = "kdrama_cache.json" 
data_lock = threading.Lock()

# --- BACKEND (THE K-DRAMA BRAIN) ---
def fetch_url(url):
    try:
        r = requests.get(url, timeout=4)
        if r.status_code == 200: return r.json().get('results', [])
    except: pass
    return []

def sync_kdrama_universe():
    print("--- SERVER: K-DRAMA SYNC STARTED ---")
    seen_ids = set()
    while True:
        current_batch = []
        base_url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&with_original_language=ko&sort_by=popularity.desc"
        urls = []
        for p in range(1, 16): urls.append(f"{base_url}&page={p}")
        genre_ids = [10749, 35, 10759, 9648, 10765] 
        for g in genre_ids:
            for p in range(1, 4): urls.append(f"{base_url}&with_genres={g}&page={p}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_url, urls)
            for res in results: process_items(res, current_batch, seen_ids)
        
        current_batch.sort(key=lambda x: x['popularity'], reverse=True)
        save_cache(current_batch)
        print(f"--- SYNC COMPLETE: {len(current_batch)} K-Dramas Loaded ---")
        time.sleep(1800) 

def process_items(items, batch, seen):
    for item in items:
        if item['id'] in seen or not item.get('poster_path'): continue
        if item.get('original_language') != 'ko': continue 

        g_ids = item.get('genre_ids', [])
        categories = ["all"]
        if 10749 in g_ids: categories.append("romance")
        if 35 in g_ids: categories.append("comedy")
        if 10759 in g_ids or 28 in g_ids: categories.append("action")
        if 9648 in g_ids or 53 in g_ids: categories.append("thriller")
        if 10765 in g_ids: categories.append("fantasy")

        batch.append({
            "id": item.get('id'), 
            "title": item.get('name'), 
            "poster": f"https://image.tmdb.org/t/p/w300{item.get('poster_path')}",
            "rating": round(item.get('vote_average', 0), 1),
            "popularity": item.get('popularity', 0),
            "categories": categories, 
            "overview": item.get('overview', 'No summary available.'),
            "year": item.get('first_air_date', '')[:4] if item.get('first_air_date') else "N/A"
        })
        seen.add(item['id'])

def save_cache(data):
    if data:
        with data_lock:
            tmp = CACHE_FILE + ".tmp"
            with open(tmp, 'w') as f: json.dump(data, f)
            os.replace(tmp, CACHE_FILE)

threading.Thread(target=sync_kdrama_universe, daemon=True).start()

# --- FRONTEND TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#1a0b1c">
    <meta name="monetag" content="k4l3j4k3l2" /> 
    <title>K-City | K-Drama Streaming</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * { -webkit-tap-highlight-color: transparent; }
        body { background: #1a0b1c; color: #fce7f3; font-family: -apple-system, BlinkMacSystemFont, Roboto, sans-serif; overflow-x: hidden; user-select: none; }
        ::-webkit-scrollbar { display: none; }
        
        .nav-active { color: #f9a8d4; border-bottom: 2px solid #f9a8d4; }
        .spinner { border: 3px solid rgba(255, 255, 255, 0.1); border-left-color: #f9a8d4; border-radius: 50%; width: 30px; height: 30px; animation: spin 0.8s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .ep-btn { background: #382039; color: #fbcfe8; border: 1px solid #502e52; min-width: 45px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 8px; font-size: 11px; font-weight: bold; cursor: pointer; }
        .ep-btn.active { background: #f9a8d4; color: #1a0b1c; border-color: #f9a8d4; }
        
        .profile-tab-btn { flex: 1; text-align: center; padding: 10px; font-weight: bold; font-size: 13px; color: #888; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .profile-tab-active { color: #f9a8d4; border-color: #f9a8d4; }

        /* AD OVERLAY STYLES */
        #ad-overlay { background: rgba(0,0,0,0.98); backdrop-filter: blur(20px); }
        .ad-box { background: #1a0b1c; border: 1px solid #db2777; border-radius: 16px; padding: 24px; width: 85%; max-width: 320px; text-align: center; box-shadow: 0 0 40px rgba(219, 39, 119, 0.3); }
    </style>
</head>
<body class="pb-32">

    <div id="ad-overlay" class="fixed inset-0 z-[9999] hidden flex flex-col items-center justify-center">
        <div class="ad-box">
            <div class="text-pink-500 text-4xl mb-4 animate-bounce"><i class="fa fa-ticket-alt"></i></div>
            <h2 class="text-xl font-black text-white mb-2 uppercase italic">Unlock Episode</h2>
            <p class="text-xs text-pink-300/70 mb-6">Watch this short ad to continue.</p>
            
            <div class="w-full h-32 bg-black rounded-xl border border-white/10 mb-6 flex items-center justify-center relative overflow-hidden group">
                <img src="https://media.giphy.com/media/l0HlO48cWp348y3Is/giphy.gif" class="absolute inset-0 w-full h-full object-cover opacity-50">
                <span class="relative z-10 text-[10px] font-bold tracking-widest bg-black/80 px-2 py-1 rounded">SPONSORED</span>
            </div>

            <button id="ad-btn" disabled class="w-full py-3 rounded-full bg-zinc-800 text-zinc-500 font-bold text-xs cursor-not-allowed transition-all">
                Wait <span id="ad-timer">10</span>s
            </button>
        </div>
    </div>

    <div id="master-loader" class="fixed inset-0 flex flex-col items-center justify-center bg-[#1a0b1c] z-[9999] transition-opacity duration-500">
        <div class="spinner mb-4" style="width:50px; height:50px; border-width:4px;"></div>
        <p class="text-[10px] font-black uppercase tracking-widest text-pink-300 animate-pulse">Entering K-City...</p>
    </div>

    <header id="ui-header" class="p-4 sticky top-0 bg-[#1a0b1c] z-[100] border-b border-white/5">
        <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2"><i class="fa fa-heart text-pink-400 text-xl"></i><h1 class="font-black text-xl tracking-tighter text-white">K-CITY</h1></div>
            <div class="relative w-1/2">
                <i class="fa fa-search absolute left-3 top-2.5 text-pink-300/50 text-xs"></i>
                <input type="text" id="search-input" oninput="showSuggestions()" placeholder="Discover..." class="w-full bg-[#382039] rounded-full py-2 pl-9 pr-4 text-xs text-pink-100 outline-none focus:ring-1 focus:ring-pink-400 placeholder-pink-300/30">
            </div>
        </div>
        <div id="suggest-box" class="absolute left-4 right-4 top-16 bg-[#2d1b30] rounded-xl hidden shadow-2xl max-h-60 overflow-y-auto z-[200] border border-pink-500/20"></div>
        <div id="cat-bar" class="flex space-x-6 overflow-x-auto text-[11px] font-bold text-pink-300/50 whitespace-nowrap uppercase tracking-wide pl-1 pb-2">
            <span onclick="setTab('all')" data-cat="all" class="cursor-pointer nav-active text-pink-300">Trending</span>
            <span onclick="setTab('romance')" data-cat="romance" class="cursor-pointer">Romance</span>
            <span onclick="setTab('comedy')" data-cat="comedy" class="cursor-pointer">Comedy</span>
            <span onclick="setTab('thriller')" data-cat="thriller" class="cursor-pointer">Thriller</span>
            <span onclick="setTab('fantasy')" data-cat="fantasy" class="cursor-pointer">Fantasy</span>
            <span onclick="setTab('action')" data-cat="action" class="cursor-pointer">Action</span>
        </div>
    </header>

    <div id="section-home" class="min-h-screen pb-10">
        <div id="grid-home" class="p-4 grid grid-cols-3 gap-3"></div>
        <div id="scroll-loader" class="py-10 flex flex-col items-center justify-center opacity-0 transition-opacity">
            <div class="spinner"></div>
        </div>
        
        <footer class="mt-8 p-6 border-t border-white/5 text-center opacity-60">
            <img src="https://www.themoviedb.org/assets/2/v4/logos/v2/blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg" class="h-4 mx-auto mb-3" alt="TMDB Logo">
            <p class="text-[8px] text-zinc-500 max-w-[200px] mx-auto leading-relaxed">
                This product uses the TMDB API but is not endorsed or certified by TMDB.
            </p>
        </footer>
    </div>

    <div id="section-player" class="hidden fixed inset-0 bg-black z-[500] overflow-y-auto">
        <div class="relative w-full aspect-video bg-black sticky top-0 z-50">
            <div id="video-loader" class="absolute inset-0 flex items-center justify-center z-10"><div class="spinner"></div></div>
            
            <iframe id="v-frame" class="w-full h-full border-0 opacity-0 relative z-20" allowfullscreen></iframe>
            
            <div onclick="closePlayer()" class="absolute top-4 left-4 bg-black/60 text-white p-2 w-8 h-8 flex items-center justify-center rounded-full cursor-pointer z-50"><i class="fa fa-chevron-left text-xs"></i></div>
            
            <div class="absolute top-4 right-4 z-50">
                <select onchange="switchServer(this.value)" class="bg-black/80 text-pink-300 text-[9px] border border-pink-500/30 rounded px-2 py-1 font-bold outline-none cursor-pointer hover:bg-black">
                    <option value="srv1">Server 1 (Fast)</option>
                    <option value="srv2">Server 2 (Backup)</option>
                    <option value="srv3">Server 3 (Alt)</option>
                </select>
            </div>
        </div>
        
        <div class="p-5 pb-32 bg-[#1a0b1c]">
            <h1 id="play-title" class="text-xl font-black text-white leading-tight mb-2"></h1>
            <div class="flex items-center gap-2 text-[10px] font-bold text-pink-200 mb-4">
                <span class="bg-pink-600 text-white px-2 py-0.5 rounded">HD</span>
                <span id="play-rating" class="border border-pink-500/30 px-2 py-0.5 rounded"></span>
                <span id="play-year" class="text-zinc-400"></span>
            </div>
            
            <p id="play-intro" class="text-xs text-zinc-400 leading-relaxed mb-6 line-clamp-3" onclick="this.classList.toggle('line-clamp-3')"></p>
            
            <div id="ep-container">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-black text-pink-500 uppercase tracking-widest">Episodes</h3>
                    <div id="season-selector" class="flex gap-2"></div>
                </div>
                <div id="episode-list" class="grid grid-cols-5 gap-2 max-h-60 overflow-y-auto"></div>
            </div>
            
            <button onclick="saveToLib()" class="mt-8 w-full py-3 bg-[#382039] text-pink-300 font-bold rounded-xl active:scale-95 transition flex items-center justify-center gap-2">
                <i class="fa fa-bookmark"></i> Add to Saved
            </button>
        </div>
    </div>

    <div id="section-profile" class="hidden min-h-screen p-4 pt-8">
        <div class="flex items-center gap-4 mb-6">
            <div class="w-16 h-16 bg-pink-900/50 rounded-full flex items-center justify-center text-pink-400 border border-pink-500/30"><i class="fa fa-user text-2xl"></i></div>
            <div><h2 class="text-xl font-black text-white">Guest User</h2><p class="text-xs text-pink-300/50">Welcome to K-City</p></div>
        </div>
        <div class="flex border-b border-white/10 mb-6">
            <div onclick="switchProfileTab('history')" id="ptab-history" class="profile-tab-btn profile-tab-active cursor-pointer"><i class="fa fa-history mr-1"></i> Watch History</div>
            <div onclick="switchProfileTab('saved')" id="ptab-saved" class="profile-tab-btn cursor-pointer"><i class="fa fa-bookmark mr-1"></i> Saved Movies</div>
        </div>
        <div id="pcontent-history" class="grid grid-cols-1 gap-3"></div>
        <div id="pcontent-saved" class="hidden grid grid-cols-3 gap-3"></div>
        <div id="empty-state" class="hidden text-center mt-10 text-zinc-500 text-xs">Nothing here yet...</div>
    </div>

    <nav class="fixed bottom-0 w-full tab-bar flex justify-around p-3 z-[100] pb-6 bg-[#1a0b1c]">
        <div onclick="navigateTo('home')" id="nav-home" class="text-center text-pink-500 cursor-pointer">
            <i class="fa fa-compass block text-xl mb-1"></i>
            <span class="text-[9px] font-bold">Discover</span>
        </div>
        <div onclick="navigateTo('profile')" id="nav-profile" class="text-center text-zinc-600 cursor-pointer">
            <i class="fa fa-user block text-xl mb-1"></i>
            <span class="text-[9px] font-bold">Profile</span>
        </div>
    </nav>

    <script>
        const API_KEY = "4cc3094d9a8a8db22ee80b5a4be6dcf9";
        let allData=[], currentFilteredData=[], displayedCount=0;
        let currentTab='all', currentItem=null, currentTvId=null;
        let isLoadingMore=false, currentSeason=1, currentEpisode=1, activeServer='srv1';
        
        // --- AD TRACKING ---
        let watchedAds = new Set(); 

        async function init() {
            try {
                const r = await fetch(`/api/data?t=${Date.now()}`);
                allData = await r.json();
                applyFilters();
                document.getElementById('master-loader').classList.add('hidden');
            } catch(e){ setTimeout(init, 2000); }
        }

        function updateTabUI(cat) { document.querySelectorAll('#cat-bar span').forEach(s => { s.classList.remove('nav-active', 'text-pink-300'); s.classList.add('text-pink-300/50'); if(s.dataset.cat === cat) { s.classList.add('nav-active', 'text-pink-300'); s.classList.remove('text-pink-300/50'); } }); }
        function setTab(cat) { currentTab=cat; updateTabUI(cat); applyFilters(); }
        function applyFilters() { if(currentTab==='all') currentFilteredData=allData; else currentFilteredData=allData.filter(i=>i.categories.includes(currentTab)); displayedCount=0; document.getElementById('grid-home').innerHTML=""; loadMoreItems(); }
        
        function loadMoreItems() {
            if(isLoadingMore) return; isLoadingMore=true;
            const loader=document.getElementById('scroll-loader');
            if(displayedCount < currentFilteredData.length) loader.classList.remove('opacity-0');
            setTimeout(() => {
                const batch = currentFilteredData.slice(displayedCount, displayedCount+15);
                if(batch.length > 0) {
                    document.getElementById('grid-home').insertAdjacentHTML('beforeend', batch.map(i => `
                        <div onclick="preparePlayer('${i.id}')" class="relative group cursor-pointer active:scale-95 transition-transform duration-100">
                            <img src="${i.poster}" loading="lazy" class="rounded-lg aspect-[2/3] object-cover bg-[#382039] shadow-lg">
                            <div class="mt-2"><h3 class="text-[10px] font-bold truncate text-pink-100">${i.title}</h3></div>
                            <div class="absolute top-1 right-1 bg-black/60 px-1.5 rounded text-[8px] font-bold text-pink-400">★ ${i.rating}</div>
                        </div>`).join(''));
                    displayedCount += 15;
                }
                loader.classList.add('opacity-0'); isLoadingMore=false;
            }, 500); 
        }
        window.addEventListener('scroll', () => { if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 300) loadMoreItems(); });

        function preparePlayer(id) { currentItem=allData.find(i=>i.id==id); if(currentItem) { addToHistory(currentItem); openPlayer(currentItem); } }
        async function openPlayer(item) {
            document.getElementById('play-title').innerText = item.title;
            document.getElementById('play-intro').innerText = item.overview;
            document.getElementById('play-rating').innerText = item.rating;
            document.getElementById('play-year').innerText = item.year;
            document.getElementById('section-player').classList.remove('hidden');
            currentTvId = item.id; 
            await fetchSeasons(item.id); 
            // Trigger Ad Logic on Episode 1 by default
            tryPlayEp(1, 1, null);
        }

        async function fetchSeasons(id) {
            try {
                const r = await fetch(`https://api.themoviedb.org/3/tv/${id}?api_key=${API_KEY}`);
                const d = await r.json();
                const seasons = d.seasons.filter(s => s.season_number > 0);
                document.getElementById('season-selector').innerHTML = seasons.map(s => `<button onclick="changeSeason(${s.season_number}, ${s.episode_count}, this)" class="px-2 py-1 rounded text-[9px] font-bold border border-pink-500/30 ${s.season_number===1?'bg-pink-600 text-white':'text-zinc-400'}">S${s.season_number}</button>`).join('');
                renderEpisodes(seasons[0]?.season_number||1, seasons[0]?.episode_count||16);
            } catch(e) {}
        }
        function changeSeason(n, c, btn) { Array.from(document.getElementById('season-selector').children).forEach(b => { b.classList.remove('bg-pink-600','text-white'); b.classList.add('text-zinc-400'); }); btn.classList.remove('text-zinc-400'); btn.classList.add('bg-pink-600', 'text-white'); renderEpisodes(n, c); }
        function renderEpisodes(s, count) { let h=''; for(let i=1; i<=count; i++) h+=`<div onclick="tryPlayEp(${s},${i},this)" class="ep-btn hover:bg-pink-500/20">${i}</div>`; document.getElementById('episode-list').innerHTML=h; }

        // --- AD LOGIC: PRE-ROLL ---
        function tryPlayEp(s, e, btn) {
            currentSeason = s; currentEpisode = e;
            const epKey = `${currentTvId}_${s}_${e}`;
            
            if(watchedAds.has(epKey)) {
                // Ad already watched, play video
                playVideoFinal(btn);
            } else {
                // Show Ad First
                triggerAd(epKey, btn);
            }
        }

        function triggerAd(epKey, btn) {
            const overlay = document.getElementById('ad-overlay');
            const btnAd = document.getElementById('ad-btn');
            const timerSpan = document.getElementById('ad-timer');
            let timeLeft = 10; // 10 Second Mandatory Wait

            overlay.classList.remove('hidden');
            btnAd.disabled = true;
            btnAd.classList.add('cursor-not-allowed', 'bg-zinc-800', 'text-zinc-500');
            btnAd.classList.remove('bg-pink-600', 'text-white', 'hover:scale-105');
            btnAd.innerHTML = `Wait <span id="ad-timer">${timeLeft}</span>s`;

            const adInterval = setInterval(() => {
                timeLeft--;
                if(document.getElementById('ad-timer')) document.getElementById('ad-timer').innerText = timeLeft;
                if(timeLeft <= 0) {
                    clearInterval(adInterval);
                    btnAd.disabled = false;
                    btnAd.innerHTML = "Skip Ad & Play Episode";
                    btnAd.classList.remove('cursor-not-allowed', 'bg-zinc-800', 'text-zinc-500');
                    btnAd.classList.add('bg-pink-600', 'text-white', 'hover:scale-105');
                    
                    btnAd.onclick = () => {
                        overlay.classList.add('hidden');
                        watchedAds.add(epKey); // Unlock this episode
                        playVideoFinal(btn);
                    };
                }
            }, 1000);
        }

        function playVideoFinal(btn) {
            document.querySelectorAll('.ep-btn').forEach(b => b.classList.remove('active'));
            if(btn) btn.classList.add('active');
            else { const buttons = document.querySelectorAll('.ep-btn'); if(buttons.length >= currentEpisode) buttons[currentEpisode-1]?.classList.add('active'); }
            refreshVideoSource();
        }
        // --- END AD LOGIC ---

        function switchServer(srv) { activeServer=srv; refreshVideoSource(); }
        function refreshVideoSource() {
            const f=document.getElementById('v-frame'), l=document.getElementById('video-loader');
            l.classList.remove('hidden'); f.classList.add('opacity-0'); f.src="";
            let url = "";
            if(activeServer==='srv1') url=`https://vidsrc.xyz/embed/tv/${currentTvId}/${currentSeason}/${currentEpisode}`;
            else if(activeServer==='srv2') url=`https://vidsrc.to/embed/tv/${currentTvId}/${currentSeason}/${currentEpisode}`;
            else if(activeServer==='srv3') url=`https://www.2embed.cc/embedtv/${currentTvId}&s=${currentSeason}&e=${currentEpisode}`;
            setTimeout(() => { f.src=url; }, 100);
            f.onload = () => { l.classList.add('hidden'); f.classList.remove('opacity-0'); };
        }

        function closePlayer() { document.getElementById('section-player').classList.add('hidden'); document.getElementById('v-frame').src=""; }
        function switchProfileTab(tab) {
            const hb=document.getElementById('ptab-history'), sb=document.getElementById('ptab-saved');
            const hc=document.getElementById('pcontent-history'), sc=document.getElementById('pcontent-saved');
            if(tab==='history') { hb.classList.add('profile-tab-active'); sb.classList.remove('profile-tab-active'); hc.classList.remove('hidden'); sc.classList.add('hidden'); renderHistory(); }
            else { sb.classList.add('profile-tab-active'); hb.classList.remove('profile-tab-active'); sc.classList.remove('hidden'); hc.classList.add('hidden'); renderSaved(); }
        }
        function saveToLib() { let s=JSON.parse(localStorage.getItem('kcity_saved')||'[]'); if(!s.find(i=>i.id===currentItem.id)) { s.unshift(currentItem); localStorage.setItem('kcity_saved', JSON.stringify(s)); alert("Saved to Profile!"); } }
        function addToHistory(item) { let h=JSON.parse(localStorage.getItem('kcity_history')||'[]'); h=h.filter(i=>i.id!==item.id); h.unshift(item); if(h.length>20) h.pop(); localStorage.setItem('kcity_history', JSON.stringify(h)); }
        function renderHistory() { const d=JSON.parse(localStorage.getItem('kcity_history')||'[]'); const el=document.getElementById('pcontent-history'); if(d.length===0) { document.getElementById('empty-state').classList.remove('hidden'); el.innerHTML=""; return; } document.getElementById('empty-state').classList.add('hidden'); el.innerHTML=d.map(i=>`<div onclick="preparePlayer('${i.id}')" class="flex gap-3 bg-[#2d1b30] p-2 rounded-lg cursor-pointer active:scale-95 transition"><img src="${i.poster}" class="w-16 h-24 object-cover rounded-md flex-shrink-0"><div class="flex flex-col justify-center"><h4 class="text-pink-100 font-bold text-xs mb-1">${i.title}</h4><span class="text-[10px] text-pink-500/50">Continue Watching</span><div class="w-full bg-black/30 h-1 mt-2 rounded-full overflow-hidden"><div class="bg-pink-600 h-full w-2/3"></div></div></div></div>`).join(''); }
        function renderSaved() { const d=JSON.parse(localStorage.getItem('kcity_saved')||'[]'); const el=document.getElementById('pcontent-saved'); if(d.length===0) { document.getElementById('empty-state').classList.remove('hidden'); el.innerHTML=""; return; } document.getElementById('empty-state').classList.add('hidden'); el.innerHTML=d.map(i=>`<div class="relative"><img src="${i.poster}" class="rounded-lg aspect-[2/3] object-cover border border-pink-500/20" onclick="preparePlayer('${i.id}')"></div>`).join(''); }
        function navigateTo(p) { const isHome=p==='home'; document.getElementById('section-home').classList.toggle('hidden', !isHome); document.getElementById('ui-header').classList.toggle('hidden', !isHome); document.getElementById('section-profile').classList.toggle('hidden', isHome); document.getElementById('nav-home').classList.toggle('text-pink-500', isHome); document.getElementById('nav-profile').classList.toggle('text-pink-500', !isHome); if(p==='profile') switchProfileTab('history'); }
        function showSuggestions() { const q=document.getElementById('search-input').value.toLowerCase(), b=document.getElementById('suggest-box'); if(q.length<2) { b.classList.add('hidden'); return; } const m=allData.filter(i=>i.title.toLowerCase().includes(q)).slice(0,5); b.innerHTML=m.map(i=>`<div onclick="preparePlayer('${i.id}')" class="p-3 flex items-center space-x-3 cursor-pointer hover:bg-pink-500/10 border-b border-pink-500/10"><img src="${i.poster}" class="w-8 h-12 rounded object-cover"><div class="text-[10px] font-bold text-pink-100">${i.title}</div></div>`).join(''); b.classList.remove('hidden'); }
        init();
    </script>
</body>
</html>
"""

# --- MONETAG SERVICE WORKER ROUTE ---
@app.route('/sw.js')
def service_worker():
    js_content = """
self.options = {
    "domain": "5gvci.com",
    "zoneId": 10506993
}
self.lary = ""
importScripts('https://5gvci.com/act/files/service-worker.min.js?r=sw')
"""
    return Response(js_content, mimetype='application/javascript')

@app.route('/api/data')
def get_data():
    with data_lock:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f: return jsonify(json.load(f))
            except: pass
    return jsonify([])

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
