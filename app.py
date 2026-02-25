import threading, time, requests, json, os
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template_string, jsonify, Response

app = Flask(__name__)

# --- CONFIGURATION ---
TMDB_API_KEY = "4cc3094d9a8a8db22ee80b5a4be6dcf9"
CACHE_FILE = "kdrama_cache.json" 
data_lock = threading.Lock()

# --- BACKEND ---
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
            "poster": f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}",
            "backdrop": f"https://image.tmdb.org/t/p/original{item.get('backdrop_path')}" if item.get('backdrop_path') else f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}",
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
    <meta name="theme-color" content="#141414">
    <meta name="monetag" content="k4l3j4k3l2" />
    <script src="https://quge5.com/88/tag.min.js" data-zone="204745" async data-cfasync="false"></script>
    <title>K-City | K-Drama Streaming</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
        * { -webkit-tap-highlight-color: transparent; box-sizing: border-box; }
        body { background: #141414; color: #ffffff; font-family: 'Inter', sans-serif; overflow-x: hidden; user-select: none; }
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        
        .spinner { border: 3px solid rgba(255, 255, 255, 0.1); border-left-color: #E50914; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        /* Netflix-style inputs & buttons */
        .search-open { width: 100%; opacity: 1; padding-left: 2.5rem; }
        .search-closed { width: 0; opacity: 0; padding: 0; border: none; }
        .ep-btn { background: #2b2b2b; color: #fff; border: 1px solid #333; min-width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .ep-btn.active { background: #E50914; color: #fff; border-color: #E50914; }
        .profile-tab-btn { flex: 1; text-align: center; padding: 12px; font-weight: 600; font-size: 14px; color: #808080; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .profile-tab-active { color: #fff; border-color: #E50914; }

        /* HEADER GRADIENT TRANSITION */
        .header-scrolled { background: #141414 !important; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }

        /* UNLOCK SCREEN STYLES */
        #unlock-screen { background-color: #000; background-size: cover; background-position: center; position: absolute; inset: 0; z-index: 50; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        #unlock-overlay-bg { position: absolute; inset: 0; background: linear-gradient(to top, rgba(20,20,20,1) 0%, rgba(0,0,0,0.6) 100%); backdrop-filter: blur(8px); z-index: -1; }
        
        .unlock-btn { background: #E50914; color: white; padding: 15px 40px; border-radius: 4px; font-weight: 800; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 4px 15px rgba(229, 9, 20, 0.4); z-index: 10; transition: all 0.3s ease; }
        .unlock-btn:active { transform: scale(0.95); }
    </style>
</head>
<body class="pb-24">

    <div id="master-loader" class="fixed inset-0 flex flex-col items-center justify-center bg-[#141414] z-[9999] transition-opacity duration-500">
        <div class="spinner mb-4"></div>
    </div>

    <header id="ui-header" class="fixed top-0 w-full z-[100] bg-gradient-to-b from-black/90 to-transparent p-4 transition-all duration-300">
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
                <h1 class="font-black text-2xl tracking-tighter text-[#E50914]">K-CITY</h1>
            </div>
            <div class="relative flex justify-end items-center w-2/3">
                <i class="fa fa-search absolute left-3 top-2.5 text-gray-400 z-10" id="search-icon" onclick="toggleSearch()"></i>
                <input type="text" id="search-input" oninput="showSuggestions()" placeholder="Titles, genres..." class="search-closed bg-black/60 border border-gray-600 rounded py-2 pr-4 text-sm text-white outline-none focus:border-white transition-all duration-300">
            </div>
        </div>
        <div id="suggest-box" class="absolute left-4 right-4 top-16 bg-[#181818] rounded border border-gray-700 hidden shadow-2xl max-h-60 overflow-y-auto z-[200]"></div>
    </header>

    <div id="section-home" class="min-h-screen">
        <div id="hero-banner" class="relative w-full h-[65vh] md:h-[80vh] bg-cover bg-center shadow-2xl">
            <div class="absolute inset-0 bg-gradient-to-t from-[#141414] via-[#141414]/40 to-black/30"></div>
            <div class="absolute bottom-10 left-4 right-4 z-10 flex flex-col justify-end">
                <h1 id="hero-title" class="text-4xl md:text-5xl font-black mb-2 leading-tight drop-shadow-lg"></h1>
                <div id="hero-meta" class="flex items-center gap-3 text-sm font-semibold text-gray-300 mb-4 drop-shadow-md"></div>
                <div class="flex gap-3 w-full md:w-1/2">
                    <button id="hero-play-btn" class="flex-1 bg-white text-black py-2.5 rounded font-bold flex items-center justify-center gap-2 hover:bg-gray-200 transition">
                        <i class="fa fa-play"></i> Play
                    </button>
                    <button id="hero-info-btn" class="flex-1 bg-[#333333]/80 text-white py-2.5 rounded font-bold flex items-center justify-center gap-2 backdrop-blur hover:bg-[#333333] transition">
                        <i class="fa fa-info-circle"></i> Info
                    </button>
                </div>
            </div>
        </div>

        <div id="rows-container" class="-mt-4 relative z-20 pb-10"></div>
    </div>

    <div id="section-player" class="hidden fixed inset-0 bg-[#141414] z-[500] overflow-y-auto">
        <div class="relative w-full aspect-video bg-black sticky top-0 z-50 shadow-2xl">
            <div id="video-container" class="w-full h-full relative bg-black">
                
                <div id="unlock-screen">
                    <div id="unlock-overlay-bg"></div>
                    <div class="text-[#E50914] text-4xl mb-4 z-10"><i class="fa fa-lock"></i></div>
                    <h2 id="lock-msg" class="text-white font-black text-xl mb-6 tracking-wide z-10 text-center px-4">PREMIUM EPISODE</h2>
                    <button id="btn-unlock-action" onclick="unlockEpisode()" class="unlock-btn">
                        WATCH WITH AD
                    </button>
                    <p class="text-[10px] text-gray-400 mt-4 z-10 font-bold tracking-widest uppercase">Support the Creators</p>
                </div>

                <iframe id="v-frame" class="w-full h-full border-0 hidden relative z-20" allowfullscreen></iframe>
            </div>

            <div onclick="closePlayer()" class="absolute top-4 left-4 bg-black/50 hover:bg-black text-white w-10 h-10 flex items-center justify-center rounded-full cursor-pointer z-[60] backdrop-blur transition"><i class="fa fa-times text-lg"></i></div>
            <div class="absolute top-4 right-4 z-[60]">
                <select onchange="switchServer(this.value)" class="bg-black/80 text-white text-xs border border-gray-600 rounded px-3 py-1.5 font-bold outline-none cursor-pointer hover:bg-black">
                    <option value="srv1">Source 1</option>
                    <option value="srv2">Source 2</option>
                    <option value="srv3">Source 3</option>
                </select>
            </div>
        </div>
        
        <div class="p-4 md:p-8 pb-32 max-w-5xl mx-auto">
            <h1 id="play-title" class="text-2xl md:text-3xl font-black text-white leading-tight mb-2"></h1>
            <div class="flex items-center gap-3 text-sm font-semibold text-gray-400 mb-6">
                <span class="text-[#46d369] font-bold">New</span>
                <span id="play-year"></span>
                <span class="border border-gray-600 px-1.5 rounded text-xs">HD</span>
                <span id="play-rating" class="flex items-center gap-1"><i class="fa fa-star text-yellow-500 text-xs"></i> </span>
            </div>
            
            <div class="flex flex-col md:flex-row gap-8">
                <div class="flex-1">
                    <p id="play-intro" class="text-sm text-gray-300 leading-relaxed mb-6"></p>
                    <button onclick="saveToLib()" class="mb-8 w-full md:w-auto px-8 py-3 bg-[#2b2b2b] hover:bg-gray-700 text-white font-bold rounded transition flex items-center justify-center gap-2"><i class="fa fa-plus"></i> My List</button>
                </div>
                
                <div id="ep-container" class="w-full md:w-1/2">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-white">Episodes</h3>
                        <div id="season-selector" class="flex gap-2"></div>
                    </div>
                    <div id="episode-list" class="grid grid-cols-4 md:grid-cols-5 gap-2 max-h-80 overflow-y-auto hide-scrollbar pr-2"></div>
                </div>
            </div>
        </div>
    </div>

    <div id="section-profile" class="hidden min-h-screen p-4 pt-20">
        <div class="flex flex-col items-center justify-center gap-3 mb-10 mt-4">
            <img src="https://wallpapers.com/images/hd/netflix-profile-pictures-1000-x-1000-qo9h82134t9nv0j0.jpg" class="w-24 h-24 rounded shadow-lg border-2 border-transparent">
            <h2 class="text-2xl font-black text-white">Who's Watching?</h2>
        </div>
        <div class="flex border-b border-gray-800 mb-6 max-w-2xl mx-auto">
            <div onclick="switchProfileTab('history')" id="ptab-history" class="profile-tab-btn profile-tab-active cursor-pointer">Continue Watching</div>
            <div onclick="switchProfileTab('saved')" id="ptab-saved" class="profile-tab-btn cursor-pointer">My List</div>
        </div>
        <div id="pcontent-history" class="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto"></div>
        <div id="pcontent-saved" class="hidden grid grid-cols-3 md:grid-cols-5 gap-3 max-w-4xl mx-auto"></div>
        <div id="empty-state" class="hidden text-center mt-16 text-gray-500 text-sm font-semibold">No activity yet.</div>
    </div>

    <nav class="fixed bottom-0 w-full flex justify-around p-3 z-[100] pb-6 bg-[#141414]/90 backdrop-blur-md border-t border-white/5">
        <div onclick="navigateTo('home')" id="nav-home" class="text-center text-white cursor-pointer transition-colors"><i class="fa fa-home block text-xl mb-1"></i><span class="text-[10px] font-bold">Home</span></div>
        <div onclick="navigateTo('profile')" id="nav-profile" class="text-center text-gray-500 cursor-pointer transition-colors"><i class="fa fa-user block text-xl mb-1"></i><span class="text-[10px] font-bold">My K-City</span></div>
    </nav>

    <script>
        const API_KEY = "4cc3094d9a8a8db22ee80b5a4be6dcf9";
        let allData=[], currentItem=null, currentTvId=null;
        let currentSeason=1, currentEpisode=1, activeServer='srv1';
        let watchedAds = new Set(); 
        let isSearchOpen = false;

        if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js'); }

        // Scroll listener for header gradient
        window.addEventListener('scroll', () => {
            const header = document.getElementById('ui-header');
            if (window.scrollY > 50) header.classList.add('header-scrolled');
            else header.classList.remove('header-scrolled');
        });

        async function init() {
            try {
                const r = await fetch(`/api/data?t=${Date.now()}`);
                allData = await r.json();
                if(allData.length > 0) { renderNetflixStyle(); }
                document.getElementById('master-loader').classList.add('hidden');
            } catch(e){ setTimeout(init, 2000); }
        }

        function toggleSearch() {
            const input = document.getElementById('search-input');
            isSearchOpen = !isSearchOpen;
            if(isSearchOpen) {
                input.classList.remove('search-closed');
                input.classList.add('search-open');
                input.focus();
            } else {
                input.classList.add('search-closed');
                input.classList.remove('search-open');
                input.value = '';
                document.getElementById('suggest-box').classList.add('hidden');
            }
        }

        function renderNetflixStyle() {
            // Setup Hero
            const hero = allData[0];
            document.getElementById('hero-banner').style.backgroundImage = `url('${hero.backdrop}')`;
            document.getElementById('hero-title').innerText = hero.title;
            document.getElementById('hero-meta').innerHTML = `<span>${hero.year}</span> <span class="border border-gray-400 px-1 text-xs">TV-MA</span> <span>★ ${hero.rating}</span>`;
            document.getElementById('hero-play-btn').onclick = () => preparePlayer(hero.id);
            document.getElementById('hero-info-btn').onclick = () => preparePlayer(hero.id);

            // Render Rows
            const container = document.getElementById('rows-container');
            container.innerHTML = '';
            
            const categories = [
                { id: 'romance', title: 'Swoonworthy Romance' },
                { id: 'action', title: 'Adrenaline Rush' },
                { id: 'comedy', title: 'Laugh Out Loud' },
                { id: 'thriller', title: 'Suspenseful Thrillers' },
                { id: 'fantasy', title: 'Sci-Fi & Fantasy' }
            ];

            // Trending Row (excluding hero)
            container.appendChild(createRow('Trending Now', allData.slice(1, 16)));

            categories.forEach(cat => {
                const items = allData.filter(i => i.categories.includes(cat.id));
                if(items.length > 0) container.appendChild(createRow(cat.title, items.slice(0, 15)));
            });
        }

        function createRow(title, items) {
            const wrapper = document.createElement('div');
            wrapper.className = 'mb-8 pl-4';
            wrapper.innerHTML = `
                <h2 class="text-white font-bold text-lg mb-3 tracking-wide">${title}</h2>
                <div class="flex gap-3 overflow-x-auto snap-x pr-4 pb-4 hide-scrollbar">
                    ${items.map(i => `
                        <div onclick="preparePlayer('${i.id}')" class="snap-start shrink-0 relative w-28 md:w-40 group cursor-pointer transition transform hover:scale-105 duration-300">
                            <img src="${i.poster}" loading="lazy" class="rounded w-full aspect-[2/3] object-cover bg-[#222]">
                        </div>
                    `).join('')}
                </div>`;
            return wrapper;
        }

        function preparePlayer(id) { 
            currentItem = allData.find(i => String(i.id) === String(id)); 
            if(currentItem) { addToHistory(currentItem); openPlayer(currentItem); } 
        }
        
        async function openPlayer(item) {
            document.getElementById('play-title').innerText = item.title;
            document.getElementById('play-intro').innerText = item.overview;
            document.getElementById('play-rating').innerHTML += item.rating;
            document.getElementById('play-year').innerText = item.year;
            document.getElementById('unlock-screen').style.backgroundImage = `url('${item.backdrop}')`;
            document.getElementById('section-player').classList.remove('hidden');
            
            currentTvId = String(item.id); 
            await fetchSeasons(item.id); 
            
            currentSeason=1; currentEpisode=1;
            renderEpisodes(1, 16); 
            
            if(watchedAds.has(currentTvId)) showVideoDirectly();
            else showLockScreen(1);
        }

        async function fetchSeasons(id) {
            try {
                const r = await fetch(`https://api.themoviedb.org/3/tv/${id}?api_key=${API_KEY}`);
                const d = await r.json();
                const seasons = d.seasons.filter(s => s.season_number > 0);
                document.getElementById('season-selector').innerHTML = seasons.map(s => `<button onclick="changeSeason(${s.season_number}, ${s.episode_count}, this)" class="px-3 py-1 rounded text-sm font-bold border border-gray-600 ${s.season_number===1?'bg-white text-black':'text-gray-400'}">Season ${s.season_number}</button>`).join('');
                renderEpisodes(seasons[0]?.season_number||1, seasons[0]?.episode_count||16);
            } catch(e) {}
        }

        function changeSeason(n, c, btn) { Array.from(document.getElementById('season-selector').children).forEach(b => { b.classList.remove('bg-white','text-black'); b.classList.add('text-gray-400'); }); btn.classList.remove('text-gray-400'); btn.classList.add('bg-white', 'text-black'); renderEpisodes(n, c); }
        function renderEpisodes(s, count) { let h=''; for(let i=1; i<=count; i++) h+=`<div onclick="switchEpisode(${s},${i},this)" class="ep-btn hover:bg-gray-700">${i}</div>`; document.getElementById('episode-list').innerHTML=h; }

        function showLockScreen(epNum) {
            const screen = document.getElementById('unlock-screen');
            const vFrame = document.getElementById('v-frame');
            const btn = document.getElementById('btn-unlock-action');
            
            btn.innerHTML = 'WATCH WITH AD';
            btn.style.background = '#E50914';
            btn.dataset.loading = "false";
            btn.style.opacity = "1";

            vFrame.classList.add('hidden'); vFrame.src = ""; 
            screen.classList.remove('hidden'); screen.style.display = 'flex';
            document.getElementById('lock-msg').innerText = `EPISODE ${epNum} LOCKED`;
        }

        function showVideoDirectly() {
            const screen = document.getElementById('unlock-screen');
            const vFrame = document.getElementById('v-frame');
            screen.classList.add('hidden'); screen.style.display = 'none';
            vFrame.classList.remove('hidden');
            refreshVideoSource();
        }

        function unlockEpisode() {
            const btn = document.getElementById('btn-unlock-action');
            if(btn.dataset.loading === "true") return;
            btn.dataset.loading = "true";
            
            btn.innerHTML = '<i class="fa fa-circle-notch fa-spin"></i> LOADING AD...';
            btn.style.opacity = "0.8";
            
            setTimeout(() => {
                watchedAds.add(String(currentTvId));
                btn.innerHTML = 'UNLOCKED';
                btn.style.background = '#46d369';
                setTimeout(() => { showVideoDirectly(); }, 800); 
            }, 2500);
        }

        function switchEpisode(s, e, btn) {
            currentSeason = s; currentEpisode = e;
            document.querySelectorAll('.ep-btn').forEach(b => b.classList.remove('active'));
            if(btn) btn.classList.add('active');
            
            if(watchedAds.has(String(currentTvId))) { showVideoDirectly(); refreshVideoSource(); } 
            else { showLockScreen(e); }
        }

        function switchServer(srv) { activeServer=srv; refreshVideoSource(); }
        
        function refreshVideoSource() {
            const f=document.getElementById('v-frame');
            let url = "";
            if(activeServer==='srv1') url=`https://vidsrc.xyz/embed/tv/${currentTvId}/${currentSeason}/${currentEpisode}`;
            else if(activeServer==='srv2') url=`https://vidsrc.to/embed/tv/${currentTvId}/${currentSeason}/${currentEpisode}`;
            else if(activeServer==='srv3') url=`https://www.2embed.cc/embedtv/${currentTvId}&s=${currentSeason}&e=${currentEpisode}`;
            f.src = url;
        }

        function closePlayer() { document.getElementById('section-player').classList.add('hidden'); document.getElementById('v-frame').src=""; }
        
        function switchProfileTab(tab) {
            const hb=document.getElementById('ptab-history'), sb=document.getElementById('ptab-saved');
            const hc=document.getElementById('pcontent-history'), sc=document.getElementById('pcontent-saved');
            if(tab==='history') { hb.classList.add('profile-tab-active'); sb.classList.remove('profile-tab-active'); hc.classList.remove('hidden'); sc.classList.add('hidden'); renderHistory(); }
            else { sb.classList.add('profile-tab-active'); hb.classList.remove('profile-tab-active'); sc.classList.remove('hidden'); hc.classList.add('hidden'); renderSaved(); }
        }

        function saveToLib() { let s=JSON.parse(localStorage.getItem('kcity_saved')||'[]'); if(!s.find(i=>String(i.id)===String(currentItem.id))) { s.unshift(currentItem); localStorage.setItem('kcity_saved', JSON.stringify(s)); alert("Added to My List!"); } }
        function addToHistory(item) { let h=JSON.parse(localStorage.getItem('kcity_history')||'[]'); h=h.filter(i=>String(i.id)!==String(item.id)); h.unshift(item); if(h.length>20) h.pop(); localStorage.setItem('kcity_history', JSON.stringify(h)); }
        
        function renderHistory() { const d=JSON.parse(localStorage.getItem('kcity_history')||'[]'); const el=document.getElementById('pcontent-history'); if(d.length===0) { document.getElementById('empty-state').classList.remove('hidden'); el.innerHTML=""; return; } document.getElementById('empty-state').classList.add('hidden'); el.innerHTML=d.map(i=>`<div onclick="preparePlayer('${i.id}')" class="relative cursor-pointer transition transform hover:scale-105 group"><img src="${i.backdrop||i.poster}" class="w-full aspect-video object-cover rounded shadow-md border border-gray-800"><div class="absolute bottom-0 left-0 right-0 bg-black/80 p-2 rounded-b"><h4 class="text-white font-bold text-xs truncate">${i.title}</h4><div class="w-full bg-gray-700 h-0.5 mt-2 rounded overflow-hidden"><div class="bg-[#E50914] h-full w-2/3"></div></div></div><i class="fa fa-play absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white/50 text-2xl group-hover:text-white transition"></i></div>`).join(''); }
        
        function renderSaved() { const d=JSON.parse(localStorage.getItem('kcity_saved')||'[]'); const el=document.getElementById('pcontent-saved'); if(d.length===0) { document.getElementById('empty-state').classList.remove('hidden'); el.innerHTML=""; return; } document.getElementById('empty-state').classList.add('hidden'); el.innerHTML=d.map(i=>`<div class="relative transition transform hover:scale-105 cursor-pointer"><img src="${i.poster}" class="rounded aspect-[2/3] object-cover" onclick="preparePlayer('${i.id}')"></div>`).join(''); }
        
        function navigateTo(p) { const isHome=p==='home'; document.getElementById('section-home').classList.toggle('hidden', !isHome); document.getElementById('ui-header').classList.toggle('hidden', !isHome); document.getElementById('section-profile').classList.toggle('hidden', isHome); document.getElementById('nav-home').classList.toggle('text-white', isHome); document.getElementById('nav-home').classList.toggle('text-gray-500', !isHome); document.getElementById('nav-profile').classList.toggle('text-white', !isHome); document.getElementById('nav-profile').classList.toggle('text-gray-500', isHome); if(p==='profile') switchProfileTab('history'); else { document.getElementById('hero-banner').classList.remove('hidden'); document.getElementById('rows-container').classList.remove('hidden'); } }
        
        function showSuggestions() { const q=document.getElementById('search-input').value.toLowerCase(), b=document.getElementById('suggest-box'); if(q.length<2) { b.classList.add('hidden'); return; } const m=allData.filter(i=>i.title.toLowerCase().includes(q)).slice(0,6); b.innerHTML=m.map(i=>`<div onclick="preparePlayer('${i.id}'); toggleSearch();" class="p-3 flex items-center space-x-3 cursor-pointer hover:bg-gray-800 border-b border-gray-700"><img src="${i.poster}" class="w-10 h-14 rounded object-cover"><div class="text-sm font-semibold text-white">${i.title}</div></div>`).join(''); b.classList.remove('hidden'); }
        
        init();
    </script>
</body>
</html>
