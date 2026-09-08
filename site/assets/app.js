
// ---------- gallery ----------
var CUSTOM_EMAIL="aXRzbm91cnk2NUBnbWFpbC5jb20=";
function setStage(b){
  var s=document.getElementById('stage'); if(!s)return;
  if(!b.dataset.src)return;
  s.src=b.dataset.src; s.style.animation='none'; void s.offsetWidth; s.style.animation='';
}
function toggleGroup(sel,me){
  document.querySelectorAll(sel).forEach(function(x){x.classList.remove('on')});
  me.classList.add('on');
}
document.querySelectorAll('.thumb,.swatch,.stylechip').forEach(function(b){
  b.addEventListener('click',function(){
    var grp;
    if(b.classList.contains('thumb'))grp='.thumb';
    else if(b.classList.contains('swatch'))grp='.swatch';
    else if(b.classList.contains('stylechip'))grp='.stylechip';
    setStage(b);
    if(grp)toggleGroup(grp,b);
  });
});
['.size'].forEach(function(sel){
  document.querySelectorAll(sel).forEach(function(b){
    b.addEventListener('click',function(){toggleGroup(sel,b)});
  });
});

// ---------- custom design form (FormSubmit, no backend needed) ----------
// The destination address is assembled at runtime from a base64 token so the
// owner's email never appears in the page source (anti-harvesting).
(function(){
  var form=document.getElementById('customForm'); if(!form)return;
  form.action='https://formsubmit.co/'+atob(CUSTOM_EMAIL);
  var msg=document.getElementById('formmsg');
  var btn=form.querySelector('button[type=submit]');
  form.addEventListener('submit',function(e){
    var name=form.querySelector('input[name=name]').value.trim(),
        email=form.querySelector('input[name=email]').value.trim(),
        idea=form.querySelector('input[name=idea]').value.trim();
    if(!name||!email||!idea){msg.style.color='#c0392b';msg.textContent='Please fill in your name, email and the idea.';e.preventDefault();return;}
    e.preventDefault();
    if(btn)btn.disabled=true;
    if(msg){msg.style.color='';msg.textContent='Sending your idea...';}
    var data=new FormData(form);
    var ok=false;
    try{
      fetch(form.action,{method:'POST',body:data,mode:'no-cors'}).then(function(){
        ok=true;
        if(msg)msg.textContent='Thank you '+name+'! Your idea is on its way. We will reply to '+email+' within 1-2 days.';
        form.reset(); if(btn)btn.disabled=false;
      }).catch(function(){fallback()});
      setTimeout(function(){if(!ok){}},1500);
    }catch(err){fallback()}
    function fallback(){
      var body='Name: '+name+'\nEmail: '+email+'\nTeam/theme: '+(form.querySelector('select[name=team]').value)+'\nGarment: '+(form.querySelector('select[name=garment]').value)+'\nIdea: '+idea+'\nSizes: '+(form.querySelector('input[name=sizes]').value)+'\nDetails: '+(form.querySelector('textarea[name=details]').value);
      window.location.href='mailto:'+atob(CUSTOM_EMAIL)+'?subject='+encodeURIComponent('Custom Design Request from '+name)+'&body='+encodeURIComponent(body);
      if(msg)msg.textContent='Opening your email app with your request - hit send and we will get back to you within 1-2 days.';
    }
  });
})();

// ---------- custom shirt popup (once per session, after scroll) ----------
(function(){
  var pop=document.getElementById('csPop');
  if(!pop)return;
  // sessionStorage: show once per browser session, not on every page
  var done;
  try{ done=sessionStorage.getItem('csPopShown'); }catch(e){}
  if(done)return;
  var shown=false;
  function maybeShow(){
    if(shown)return;
    var sc=window.scrollY||0;
    // show once the visitor has scrolled ~ 1.5 viewport heights
    if(sc > (window.innerHeight||800)*1.5){
      shown=true;
      pop.hidden=false;
      requestAnimationFrame(function(){requestAnimationFrame(function(){pop.classList.add('on');});});
      try{ sessionStorage.setItem('csPopShown','1'); }catch(e){}
    }
  }
  window.addEventListener('scroll',maybeShow,{passive:true});
  maybeShow();
  var close=document.getElementById('csPopClose');
  var go=document.getElementById('csPopGo');
  function dismiss(){
    pop.classList.remove('on');
    setTimeout(function(){pop.hidden=true;},350);
  }
  if(close)close.addEventListener('click',dismiss);
  if(go)go.addEventListener('click',function(){
    dismiss();
    var target=document.querySelector('.customsec')||document.querySelector('.customform');
    if(target)target.scrollIntoView({behavior:'smooth',block:'start'});
  });
})();

// ---------- reveal safety net: never leave content invisible ----------
setTimeout(function(){
  document.querySelectorAll('.reveal').forEach(function(e){e.classList.add('in')});
},2600);

// ---------- scroll reveal ----------
(function(){
  var els=[].slice.call(document.querySelectorAll('.reveal'));
  if(!('IntersectionObserver' in window)){els.forEach(function(e){e.classList.add('in')});return;}
  var io=new IntersectionObserver(function(en){
    en.forEach(function(e,i){
      if(e.isIntersecting){
        var el=e.target;
        setTimeout(function(){el.classList.add('in')}, Math.min(i*70,350));
        io.unobserve(el);
      }
    });
  },{rootMargin:'0px 0px -8% 0px',threshold:.06});
  els.forEach(function(e){io.observe(e)});
})();

// ---------- count up ----------
(function(){
  var st=[].slice.call(document.querySelectorAll('[data-count]'));
  if(!st.length||!('IntersectionObserver' in window))return;
  var io=new IntersectionObserver(function(en){
    en.forEach(function(e){
      if(!e.isIntersecting)return;
      var el=e.target,to=parseInt(el.dataset.count,10),t0=null;
      function step(ts){
        if(!t0)t0=ts; var p=Math.min((ts-t0)/1100,1);
        el.textContent=Math.floor(to*(1-Math.pow(1-p,3))).toLocaleString();
        if(p<1)requestAnimationFrame(step);
      }
      requestAnimationFrame(step); io.unobserve(el);
    });
  },{threshold:.4});
  st.forEach(function(e){io.observe(e)});
})();

// ---------- kickoff countdown ----------
(function(){
  var box=document.querySelector('.cd'); if(!box)return;
  var end=new Date(box.dataset.deadline).getTime();
  var d=document.getElementById('cd-d'),h=document.getElementById('cd-h'),
      m=document.getElementById('cd-m'),s=document.getElementById('cd-s');
  function pad(n){return (n<10?'0':'')+n}
  function tick(){
    var gap=end-Date.now();
    if(gap<0){gap=0}
    var dd=Math.floor(gap/864e5),hh=Math.floor(gap%864e5/36e5),
        mm=Math.floor(gap%36e5/6e4),ss=Math.floor(gap%6e4/1e3);
    d.childNodes[0].nodeValue=dd; h.childNodes[0].nodeValue=pad(hh);
    m.childNodes[0].nodeValue=pad(mm); s.childNodes[0].nodeValue=pad(ss);
  }
  tick(); setInterval(tick,1000);
})();


// ---------- sticky header + back to top ----------
(function(){
  var hd=document.querySelector('header'), tt=document.getElementById('totop');
  function on(){
    var y=window.scrollY||0;
    hd&&hd.classList.toggle('stuck',y>10);
    tt&&tt.classList.toggle('on',y>700);
  }
  window.addEventListener('scroll',on,{passive:true}); on();
  tt&&tt.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'})});
})();

// ---------- collection filter / search / sort (team pages + /search/) ----------
// Four independent dimensions: garment (chip[data-f]), team (chip[data-team]),
// style/theme (chip[data-st], read from the card's data-theme attribute) and
// price (#price select). A page only emits the controls it offers, so the
// other dimensions stay at their defaults and behaviour is unchanged.
(function(){
  var grid=document.getElementById('pg'); if(!grid)return;
  var cards=[].slice.call(grid.children);
  var q=document.getElementById('q'), sort=document.getElementById('sort'),
      count=document.getElementById('count'), nores=document.getElementById('nores');
  var typeFilter='all', teamFilter='all', styleFilter='all', priceFilter='any';
  function price(c){return parseFloat(c.querySelector('.price').textContent.replace('$',''))}
  function name(c){return c.querySelector('h3').textContent.toLowerCase()}
  function typeOf(c){return c.getAttribute('data-type')||c.querySelector('.meta').textContent.trim()}
  function teamOf(c){return c.getAttribute('data-team')||''}
  function styleOf(c){return c.getAttribute('data-theme')||''}
  function inPrice(p){
    if(priceFilter==='u20')return p<20;
    if(priceFilter==='20-25')return p>=20&&p<25;
    if(priceFilter==='25-30')return p>=25&&p<30;
    if(priceFilter==='o30')return p>=30;
    return true;
  }
  function apply(){
    var term=(q?q.value:'').toLowerCase().trim(), n=0;
    cards.forEach(function(c){
      var ok=(typeFilter==='all'||typeOf(c)===typeFilter)&&
             (teamFilter==='all'||teamOf(c)===teamFilter)&&
             (styleFilter==='all'||styleOf(c)===styleFilter)&&
             inPrice(price(c))&&
             (!term||c.textContent.toLowerCase().indexOf(term)>-1);
      c.style.display=ok?'':'none'; if(ok){n++;c.classList.add('in');}
    });
    if(count)count.textContent=n+' design'+(n===1?'':'s');
    if(nores)nores.style.display=n?'none':'block';
  }
  function resort(){
    var v=sort.value, arr=cards.slice();
    if(v==='lo')arr.sort(function(a,b){return price(a)-price(b)});
    if(v==='hi')arr.sort(function(a,b){return price(b)-price(a)});
    if(v==='az')arr.sort(function(a,b){return name(a)<name(b)?-1:1});
    arr.forEach(function(c){grid.appendChild(c)});
  }
  function markType(v){document.querySelectorAll('.chip[data-f]').forEach(function(x){
    x.classList.toggle('on',x.getAttribute('data-f')===v);});}
  function markTeam(v){document.querySelectorAll('.chip[data-team]').forEach(function(x){
    x.classList.toggle('on',x.getAttribute('data-team')===v);});}
  function markStyle(v){document.querySelectorAll('.chip[data-st]').forEach(function(x){
    x.classList.toggle('on',x.getAttribute('data-st')===v);});}
  if(q)q.addEventListener('input',apply);
  if(sort)sort.addEventListener('change',resort);
  document.querySelectorAll('.chip[data-f]').forEach(function(b){
    b.addEventListener('click',function(){typeFilter=b.getAttribute('data-f');markType(typeFilter);apply();});
  });
  document.querySelectorAll('.chip[data-team]').forEach(function(b){
    b.addEventListener('click',function(){teamFilter=b.getAttribute('data-team');markTeam(teamFilter);apply();});
  });
  document.querySelectorAll('.chip[data-st]').forEach(function(b){
    b.addEventListener('click',function(){styleFilter=b.getAttribute('data-st');markStyle(styleFilter);apply();});
  });
  var priceSel=document.getElementById('price');
  if(priceSel)priceSel.addEventListener('change',function(){priceFilter=priceSel.value;apply();});
  // Deep links: /search/?q=... (header search + SearchAction), ?t=team,
  // ?g=garment, ?st=style (the landing quick-finder chips deep-link styles)
  var u=new URLSearchParams(location.search), tu=u.get('t'), gu=u.get('g'),
      su=u.get('st'), uq=u.get('q');
  if(gu)typeFilter=gu; if(tu)teamFilter=tu; if(su)styleFilter=su; if(uq&&q)q.value=uq;
  markType(typeFilter); markTeam(teamFilter); markStyle(styleFilter); apply();
})();

// ---------- global design search: live suggestions for every .gsearch ----------
// One shared index (assets/search-index.json) powers the header search on
// every page, the landing-page quick finder and the /search/ page input.
// Suggestions link straight to product pages; "See all results" and Enter
// land on /search/?q=... with the term pre-applied - the same URL the
// SearchAction schema advertises.
(function(){
  var inputs=[].slice.call(document.querySelectorAll('.gsearch'));
  if(!inputs.length)return;
  var ROOT=document.body.getAttribute('data-root')||'./';
  var DATA=null, pend=null;
  function load(){
    if(pend)return pend;
    pend=fetch(ROOT+'assets/search-index.json',{cache:'force-cache'})
      .then(function(r){return r.json()})
      .catch(function(){return null;});
    pend.then(function(d){if(Array.isArray(d))DATA=d;});
    return pend;
  }
  function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}
  function imgFor(i){return /^https?:/.test(i)?i:ROOT+i;}
  function allUrl(term){return ROOT+'search/?q='+encodeURIComponent(term);}
  function matches(term){
    if(!DATA)return [];
    term=term.toLowerCase();
    var out=[];
    for(var i=0;i<DATA.length;i++){
      var it=DATA[i], n=it.n.toLowerCase(), s=0;
      if(n.indexOf(term)===0)s=3;
      else if(n.indexOf(term)>-1)s=2;
      else if((it.k||'').indexOf(term)>-1)s=1;
      if(s>0)out.push([s,it]);
    }
    out.sort(function(a,b){return b[0]-a[0]||a[1].p-b[1].p;});
    return out.slice(0,8).map(function(x){return x[1];});
  }
  function render(dd,term){
    var list=matches(term);
    var html='';
    for(var i=0;i<list.length;i++){
      var it=list[i];
      html+='<a class="gs-item" href="'+ROOT+it.u+'" data-i="'+i+'">'
           +'<img src="'+imgFor(it.i)+'" alt="" width="40" height="48" loading="lazy">'
           +'<span class="gs-txt"><span class="gs-n">'+esc(it.n)
           +(it.h?' <span class="gs-hot">Trending</span>':'')
           +'</span><span class="gs-m">'+esc(it.ts)+' · '+esc(it.g)+' · $'+it.p.toFixed(2)+'</span></span></a>';
    }
    html+='<a class="gs-all" href="'+allUrl(term)+'">See all results for “'+esc(term)+'” &rarr;</a>';
    dd.innerHTML=html; dd.hidden=false;
  }
  var pairs=[];
  inputs.forEach(function(inp){
    var wrap=inp.closest('.gs, .navsearch')||inp.parentElement;
    var dd=document.createElement('div');
    dd.className='gs-dd'; dd.hidden=true; dd.setAttribute('role','listbox');
    wrap.appendChild(dd);
    var active=0, pair=null;
    function items(){return [].slice.call(dd.querySelectorAll('.gs-item'));}
    function close(){dd.hidden=true;}
    function markActive(){items().forEach(function(el,i){el.classList.toggle('on',i===active);});}
    function open(){
      var term=inp.value.trim();
      if(term.length<2){close();return;}
      render(dd,term); active=0; markActive();
    }
    function pairClose(){pair&&pair.close();}
    pair={close:close};
    inp.addEventListener('input',open);
    inp.addEventListener('focus',function(){load(); if(inp.value.trim().length>=2)open();});
    inp.addEventListener('keydown',function(e){
      if(e.key==='Escape'){close();return;}
      if(dd.hidden)return;
      if(e.key==='ArrowDown'||e.key==='ArrowUp'){
        e.preventDefault();
        var n=items().length; if(!n)return;
        active=(active+(e.key==='ArrowDown'?1:n-1))%n; markActive();
      } else if(e.key==='Enter'){
        var it=items()[active];
        if(it){e.preventDefault();window.location.href=it.getAttribute('href');}
        else if(inp.value.trim()){e.preventDefault();window.location.href=allUrl(inp.value.trim());}
      }
    });
    inp.addEventListener('blur',function(){setTimeout(function(){dd.hidden=true;},150);});
    dd.addEventListener('mousedown',function(e){e.preventDefault();});
    pairs.push(pair);
  });
  document.addEventListener('mousedown',function(e){
    pairs.forEach(function(p){p.close();});
  });
  // "/" jumps to the header search from anywhere on the page (except while
  // the visitor is already typing in a field).
  document.addEventListener('keydown',function(e){
    if(e.key!=='/')return;
    var t=document.activeElement&&document.activeElement.tagName;
    if(t==='INPUT'||t==='TEXTAREA'||t==='SELECT')return;
    var h=document.querySelector('.navsearch .gsearch')||document.querySelector('.gsearch');
    if(h){e.preventDefault();h.focus();}
  });
  load();
})();

// ---------- mobile "find your design" pill (landing + team pages) ----------
// Keeps a phone visitor one tap from the search while they scroll: the pill
// appears after the first scroll and smooth-scrolls back to the finder
// (or the sticky collection toolbar on team pages) and focuses the box.
(function(){
  var p=document.getElementById('findpill'); if(!p)return;
  var target=document.querySelector(p.getAttribute('data-target')||'#quickfind');
  if(!target)return;
  var field=target.querySelector('input.gsearch, input#q');
  function on(){p.classList.toggle('on',(window.scrollY||0)>420);}
  window.addEventListener('scroll',on,{passive:true}); on();
  p.addEventListener('click',function(){
    target.scrollIntoView({behavior:'smooth',block:'start'});
    if(field)setTimeout(function(){try{field.focus({preventScroll:true});}catch(e){field.focus();}},450);
  });
})();

// ---------- quick view: peek at a design without leaving the grid ----------
// Every card carries a .qv button (sibling of the card link, never nested
// inside it). One shared modal is built once and refilled from the card's
// own DOM, so no product data is duplicated across the 127 cards. The CTA
// hands off to the full product page - sizes and checkout live there.
(function(){
  var qs=[].slice.call(document.querySelectorAll('.card .qv'));
  if(!qs.length)return;
  var modal=document.createElement('div');
  modal.className='qvmodal'; modal.hidden=true;
  modal.innerHTML='<div class="qv-overlay"></div>'
    +'<div class="qv-box" role="dialog" aria-modal="true" aria-label="Quick view">'
    +'<button class="qv-close" type="button" aria-label="Close quick view">&#10005;</button>'
    +'<div class="qv-imgs"><img class="qv-front" alt="" width="150" height="178">'
    +'<img class="qv-back" alt="" width="150" height="178"></div>'
    +'<div class="qv-info"><span class="qv-team"></span><h3 class="qv-name"></h3>'
    +'<span class="qv-meta"></span><span class="qv-price"></span>'
    +'<a class="btn block qv-cta" href="#">View full details &amp; buy &rarr;</a>'
    +'<p class="muted qv-note">Size, style and colourway are chosen on the product page before checkout.</p>'
    +'</div></div>';
  document.body.appendChild(modal);
  var closeBtn=modal.querySelector('.qv-close');
  function pretty(s){return (s||'').replace(/-/g,' ').replace(/\b\w/g,function(ch){return ch.toUpperCase();});}
  function open(card){
    var a=card.querySelector('a'), front=card.querySelector('.ph > img'),
        back=card.querySelector('.ph img.alt'),
        name=card.querySelector('h3'), meta=card.querySelector('.meta'),
        priceEl=card.querySelector('.price');
    if(!a||!front)return;
    var b=modal.querySelector('.qv-back');
    modal.querySelector('.qv-front').src=front.getAttribute('src');
    if(back){b.src=back.getAttribute('src');b.hidden=false;}else{b.hidden=true;}
    modal.querySelector('.qv-name').textContent=name?name.textContent:'';
    modal.querySelector('.qv-team').textContent=pretty(card.getAttribute('data-team'));
    modal.querySelector('.qv-meta').textContent=meta?meta.textContent:'';
    modal.querySelector('.qv-price').textContent=priceEl?priceEl.textContent:'';
    modal.querySelector('.qv-cta').href=a.getAttribute('href');
    modal.hidden=false;
    requestAnimationFrame(function(){modal.classList.add('on');});
    document.body.style.overflow='hidden';
    closeBtn.focus();
  }
  function close(){
    modal.classList.remove('on');
    setTimeout(function(){modal.hidden=true;},220);
    document.body.style.overflow='';
  }
  qs.forEach(function(b){
    b.addEventListener('click',function(e){
      e.preventDefault(); e.stopPropagation();
      open(b.closest('.card'));
    });
  });
  closeBtn.addEventListener('click',close);
  modal.querySelector('.qv-overlay').addEventListener('click',close);
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&!modal.hidden)close();
  });
})();
