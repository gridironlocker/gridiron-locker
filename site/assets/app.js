
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
// Thumbnails only. A product page has no style / size / colour selector by
// design: Gridiron Locker presents the design, Viralstyle configures and sells
// it. The gallery is imagery, not a purchase control.
document.querySelectorAll('.thumb').forEach(function(b){
  b.addEventListener('click',function(){setStage(b);toggleGroup('.thumb',b);});
});

// Colourway mockups are gallery previews, not selectors. Clicking one only
// swaps the stage image; style/colour/size are still chosen on Viralstyle.
document.querySelectorAll('.cwtile').forEach(function(b,i){
  b.addEventListener('click',function(){
    setStage(b);
    try{gtag('event','colorway_interaction',{
      item_id:(document.querySelector('main.pdp-page')||{}).dataset&&document.querySelector('main.pdp-page').dataset.slug,
      index:i+1,destination:'gallery'
    });}catch(e){}
  });
});

// ---------- creator attribution: referral param -> persistent cookie ----------
// Creator collab pages (e.g. Joe's Michigan Locker at /michigan/joe/) send
// visitors through ?creator=<ID>. The first such touch sets a persistent
// cookie (gl_creator, 90-day sliding TTL); while that cookie is present the
// outbound Viralstyle hand-off on ANY page is tagged with creator=<ID> +
// UTM before the click, so an order stays attributed to the creator even
// when the buyer later returns via search, a bookmark or a deep link.
// Commission reconciliation is an off-site exercise (ops/creators) - this
// block is purely the attribution plumbing and never shows a rate to users.
(function(){
  var KEY='gl_creator', TTL=90*86400;
  function setCk(v){try{document.cookie=KEY+'='+encodeURIComponent(v)+'; max-age='+TTL+'; path=/; SameSite=Lax';}catch(e){}}
  function cur(){
    try{var m=document.cookie.match(new RegExp('(?:^|; )'+KEY+'=([^;]*)'));return m?m[1]:'';}catch(e){return ''}
  }
  var p='';
  try{p=(new URLSearchParams(location.search).get('creator')||'').trim().toUpperCase();}catch(e){}
  if(p&&/^[A-Z0-9_-]{1,32}$/.test(p)&&cur()!==p){
    setCk(p);
    try{gtag('event','creator_attribution_set',{creator_id:p,page:location.pathname,referrer:document.referrer||''});}catch(e){}
  }
  var c=cur();
  window.GL_CREATOR=c;
  if(!c)return;
  var onCreatorPage=!!document.body.getAttribute('data-creator-page');
  try{
    gtag('event',onCreatorPage?'creator_page_view':'creator_session',{
      creator_id:onCreatorPage?document.body.getAttribute('data-creator-page'):c,
      page:location.pathname
    });
  }catch(e){}
  // Tag every outbound checkout link (Shop Now on product pages, any direct
  // creator CTA) so the order URL itself carries the attribution.
  var tag='creator='+encodeURIComponent(c)+'&utm_source=creator&utm_medium=referral&utm_campaign=creator-'+encodeURIComponent(c);
  document.querySelectorAll('a[href*="viralstyle.com"]').forEach(function(a){
    var h=a.getAttribute('href');
    if(!h||/[?&](creator|utm_source)=/.test(h))return;
    a.setAttribute('href',h+(h.indexOf('?')<0?'?':'&')+tag);
  });
})();

// ---------- SHOP NOW hand-off tracking ----------
// The only conversion action on a product page. Every button reports its
// placement (hero / apparel / footer_band / sticky_bar) so the metric that
// matters - product landing page -> Viralstyle click-through rate - is
// measurable, and so we can see WHICH CTA earns the click. The creator
// dimension (window.GL_CREATOR, set above from the persistent cookie) is
// attached to every event so attributed vs organic hand-offs split cleanly.
document.querySelectorAll('a.shopnow').forEach(function(a){
  a.addEventListener('click',function(){
    var d=a.dataset||{};
    try{gtag('event','shop_now_click',{
      item_id:d.slug,value:parseFloat(d.price||'0'),currency:'USD',
      collection:d.collection,placement:d.placement,creator:window.GL_CREATOR||'',
      destination:'viralstyle.com'
    });}catch(e){}
    // legacy event name kept so existing GA4 reports do not break
    try{gtag('event','viralstyle_checkout_click',{
      item:d.slug,price:parseFloat(d.price||'0'),collection:d.collection,
      placement:d.placement,creator:window.GL_CREATOR||'',destination:'viralstyle.com'
    });}catch(e){}
    try{gtag('event','viralstyle_redirect',{
      item_id:d.slug,value:parseFloat(d.price||'0'),currency:'USD',
      collection:d.collection,placement:d.placement,creator:window.GL_CREATOR||'',
      destination:'viralstyle.com'
    });}catch(e){}
  });
});

// ---------- product landing analytics ----------
(function(){
  var page=document.querySelector('main.pdp-page');
  if(!page)return;
  var d=page.dataset||{};
  try{gtag('event','product_page_view',{
    item_id:d.slug,value:parseFloat(d.price||'0'),currency:'USD',
    collection:d.collection
  });}catch(e){}
  document.querySelectorAll('#related .related a[href*="/shop/"]').forEach(function(a){
    a.addEventListener('click',function(){
      try{gtag('event','related_product_click',{
        item_id:d.slug,related:a.getAttribute('href'),collection:d.collection
      });}catch(e){}
    });
  });
  document.querySelectorAll('a.col-link').forEach(function(a){
    a.addEventListener('click',function(){
      try{gtag('event','collection_click',{
        item_id:d.slug,collection:a.dataset.collection||d.collection,
        href:a.getAttribute('href')
      });}catch(e){}
    });
  });
})();

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
      // read() tolerates a field that is not on this version of the form -
      // the mailto fallback must never throw, it is the last resort.
      function read(sel){var el=form.querySelector(sel);return el?el.value:'';}
      var body='Name: '+name+'\nEmail: '+email+'\nTeam/theme: '+read('select[name=team]')+'\nGarment: '+read('select[name=garment]')+'\nIdea: '+idea+'\nDetails: '+read('textarea[name=details]');
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
    if(target){target.scrollIntoView({behavior:'smooth',block:'start'});return;}
    // no custom section on this page - send them to the one on the homepage
    location.href=(document.body.getAttribute('data-root')||'./')+'#custom-design';
  });
})();

// ---------- product rails: arrow controls (pointer devices) ----------
// Touch swipes the rail natively; the arrows page it by one viewport-width
// of tiles and disable themselves at each end so they never lie.
(function(){
  var navs=[].slice.call(document.querySelectorAll('.rail-nav'));
  if(!navs.length)return;
  navs.forEach(function(nav){
    var rail=document.getElementById(nav.getAttribute('data-rail'));
    if(!rail)return;
    var btns=[].slice.call(nav.querySelectorAll('.rn'));
    function sync(){
      var max=rail.scrollWidth-rail.clientWidth-2;
      btns.forEach(function(b){
        var back=b.getAttribute('data-dir')==='-1';
        b.disabled = max<=0 || (back ? rail.scrollLeft<=2 : rail.scrollLeft>=max);
      });
    }
    var calm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    btns.forEach(function(b){
      b.addEventListener('click',function(){
        var step=Math.max(240,Math.round(rail.clientWidth*0.86));
        rail.scrollBy({left:step*parseInt(b.getAttribute('data-dir'),10),
                       behavior:calm?'auto':'smooth'});
      });
    });
    rail.addEventListener('scroll',sync,{passive:true});
    window.addEventListener('resize',sync);
    sync();
  });
})();

// ---------- mobile shopping bar (homepage) ----------
// A compact "Shop by team / Trending / All designs" bar so a visitor deep in
// the page never has to scroll back to the header. It appears once the hero
// is gone and hides again over the footer, where the same links already are.
(function(){
  var bar=document.getElementById('mobshop');
  if(!bar)return;
  var hero=document.getElementById('hero'), foot=document.querySelector('footer');
  var nearFooter=false;
  if(foot&&'IntersectionObserver' in window){
    new IntersectionObserver(function(en){
      nearFooter=en[0].isIntersecting; update();
    },{rootMargin:'0px 0px -40% 0px'}).observe(foot);
  }
  function update(){
    var past=(window.scrollY||0) > (hero?hero.offsetHeight*0.75:400);
    var show=past&&!nearFooter;
    if(show===!bar.hidden)return;
    bar.hidden=!show;
    document.body.classList.toggle('has-mobshop',show);
  }
  window.addEventListener('scroll',update,{passive:true});
  window.addEventListener('resize',update);
  update();
})();

// ---------- favourites (device-side, no backend) ----------
(function(){
  var key='gl_favs';
  function read(){ try{return JSON.parse(localStorage.getItem(key)||'[]');}catch(e){return [];} }
  function write(a){ try{localStorage.setItem(key,JSON.stringify(a));}catch(e){} }
  var msg=document.getElementById('favMsg');
  function toast(t){
    if(!msg)return;
    msg.textContent=t; msg.hidden=false; msg.classList.add('on');
    clearTimeout(msg._t); msg._t=setTimeout(function(){msg.classList.remove('on');msg.hidden=true;},1600);
  }
  document.querySelectorAll('.card .fav').forEach(function(b){
    var slug=b.getAttribute('data-slug');
    function draw(){
      var on=read().indexOf(slug)>-1;
      b.classList.toggle('on',on); b.setAttribute('aria-pressed',on?'true':'false');
    }
    draw();
    b.addEventListener('click',function(e){
      e.preventDefault(); e.stopPropagation();
      var a=read(), i=a.indexOf(slug), card=b.closest('.card'),
          nm=card?card.querySelector('h3').textContent:'design';
      if(i>-1){a.splice(i,1); toast('Removed "'+nm+'" from favourites.');}
      else{a.unshift(slug); toast('Saved "'+nm+'" to favourites.');}
      write(a); draw();
    });
  });
})();

// ---------- newsletter signup (FormSubmit, no backend needed) ----------
(function(){
  var form=document.getElementById('newsForm'); if(!form)return;
  form.action='https://formsubmit.co/'+atob(CUSTOM_EMAIL);
  var msg=document.getElementById('newsMsg'), btn=form.querySelector('button');
  form.addEventListener('submit',function(e){
    e.preventDefault();
    var email=form.querySelector('input[name=email]').value.trim();
    if(!email||email.indexOf('@')<1){
      if(msg){msg.style.color='#c0392b';msg.textContent='Please enter a valid email address.';}
      return;
    }
    if(btn)btn.disabled=true;
    if(msg){msg.style.color='';msg.textContent='Joining the locker...';}
    fetch(form.action,{method:'POST',body:new FormData(form),mode:'no-cors'}).then(function(){
      if(msg)msg.textContent='Welcome to the locker. Check your inbox to confirm.';
      form.reset(); if(btn)btn.disabled=false;
    }).catch(function(){
      if(msg)msg.textContent='Almost there - email us directly to join.';
      if(btn)btn.disabled=false;
    });
  });
})();

// ---------- scroll reveal (progressive enhancement: never hide without JS) ----------
// The `.pre` gate is added HERE, at runtime, so content is visible by default:
// if this file is blocked, slow, or an earlier statement throws, nothing is
// ever hidden and the page still paints in full (no white screen). When this
// runs (deferred, before first paint), below-fold elements hide and fade up
// on scroll; in-viewport elements are revealed synchronously in the same task
// so there is no flash.
(function(){
  var els=[].slice.call(document.querySelectorAll('.reveal'));
  if(!els.length)return;
  els.forEach(function(e){e.classList.add('pre')});
  function inView(el){
    try{
      var r=el.getBoundingClientRect(), h=window.innerHeight||800;
      return r.top < h*0.94 && r.bottom > 0;
    }catch(err){return true;}
  }
  var below=[];
  els.forEach(function(e){ if(inView(e)){e.classList.add('in');} else {below.push(e);} });
  if(!below.length)return;
  if(!('IntersectionObserver' in window)){below.forEach(function(e){e.classList.add('in')});return;}
  var io=new IntersectionObserver(function(en){
    en.forEach(function(e,i){
      if(e.isIntersecting){
        var el=e.target;
        setTimeout(function(){el.classList.add('in')}, Math.min(i*70,350));
        io.unobserve(el);
      }
    });
  },{rootMargin:'0px 0px -8% 0px',threshold:.06});
  below.forEach(function(e){io.observe(e)});
  // Safety net: never leave content invisible (slow IO, odd embeds, no scroll).
  setTimeout(function(){
    below.forEach(function(e){e.classList.add('in')});
  },2600);
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

// ---------- shop filters: search + dropdowns + sort (team pages + /search/) ----------
// Four independent dimensions: garment (#fType), team (#fTeam), style/theme
// (#fStyle, read from the card's data-theme attribute) and price (#price).
// A page only emits the controls it offers, so the other dimensions stay at
// their defaults and behaviour is unchanged. Legacy .chip buttons are still
// honoured if a page emits them, so older markup keeps working.
(function(){
  var grid=document.getElementById('pg'); if(!grid)return;
  var cards=[].slice.call(grid.children);
  var q=document.getElementById('q'), sort=document.getElementById('sort'),
      count=document.getElementById('count'), nores=document.getElementById('nores');
  var selType=document.getElementById('fType'), selTeam=document.getElementById('fTeam'),
      selStyle=document.getElementById('fStyle'), priceSel=document.getElementById('price');
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
    if(!sort)return;
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
  function hasOpt(sel,v){
    if(!sel)return true;
    for(var i=0;i<sel.options.length;i++){if(sel.options[i].value===v)return true;}
    return false;
  }
  function syncSel(){
    if(selType&&hasOpt(selType,typeFilter))selType.value=typeFilter;
    if(selTeam&&hasOpt(selTeam,teamFilter))selTeam.value=teamFilter;
    if(selStyle&&hasOpt(selStyle,styleFilter))selStyle.value=styleFilter;
    if(priceSel&&hasOpt(priceSel,priceFilter))priceSel.value=priceFilter;
  }
  if(q)q.addEventListener('input',apply);
  if(sort)sort.addEventListener('change',resort);
  if(selType)selType.addEventListener('change',function(){typeFilter=selType.value;markType(typeFilter);apply();});
  if(selTeam)selTeam.addEventListener('change',function(){teamFilter=selTeam.value;markTeam(teamFilter);apply();});
  if(selStyle)selStyle.addEventListener('change',function(){styleFilter=selStyle.value;markStyle(styleFilter);apply();});
  document.querySelectorAll('.chip[data-f]').forEach(function(b){
    b.addEventListener('click',function(){typeFilter=b.getAttribute('data-f');markType(typeFilter);syncSel();apply();});
  });
  document.querySelectorAll('.chip[data-team]').forEach(function(b){
    b.addEventListener('click',function(){teamFilter=b.getAttribute('data-team');markTeam(teamFilter);syncSel();apply();});
  });
  document.querySelectorAll('.chip[data-st]').forEach(function(b){
    b.addEventListener('click',function(){styleFilter=b.getAttribute('data-st');markStyle(styleFilter);syncSel();apply();});
  });
  if(priceSel)priceSel.addEventListener('change',function(){priceFilter=priceSel.value;apply();});
  // Collection switcher: a plain dropdown that navigates (collection pages).
  var selCol=document.getElementById('fCollection');
  if(selCol)selCol.addEventListener('change',function(){if(selCol.value)location.href=selCol.value;});
  // Clear all: back to the full grid.
  var clear=document.getElementById('clearFilters');
  if(clear)clear.addEventListener('click',function(){
    typeFilter='all';teamFilter='all';styleFilter='all';priceFilter='any';
    if(q)q.value=''; if(sort)sort.value='feat';
    markType('all');markTeam('all');markStyle('all');syncSel();resort();apply();
    if(q)q.focus();
  });
  // Deep links: /search/?q=... (header search + SearchAction), ?t=team,
  // ?g=garment, ?st=style (the landing quick-finder chips deep-link styles)
  var u=new URLSearchParams(location.search), tu=u.get('t'), gu=u.get('g'),
      su=u.get('st'), uq=u.get('q');
  if(gu&&hasOpt(selType,gu))typeFilter=gu;
  if(tu&&hasOpt(selTeam,tu))teamFilter=tu;
  if(su&&hasOpt(selStyle,su))styleFilter=su;
  if(uq&&q)q.value=uq;
  markType(typeFilter); markTeam(teamFilter); markStyle(styleFilter); syncSel(); apply();
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

// ---------- quick view: peek at a design without leaving the grid ----------
// Every card carries a .qv button (sibling of the card link, never nested
// inside it). One shared modal is built once and refilled from the card's
// own DOM, so no product data is duplicated across the 127 cards. The CTA
// hands off to the full product landing page; Viralstyle handles checkout.
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
    +'<a class="btn block qv-cta" href="#">See the full design &rarr;</a>'
    +'<p class="muted qv-note">The design story, apparel styles, colours and sizing are on the product page. Orders are completed on Viralstyle.</p>'
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
