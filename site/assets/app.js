
// ---------- analytics consent ----------
// Google Analytics is opt-in. The tag itself is only injected by
// window.glLoadAnalytics() (see head()), and only after this banner records a
// choice in the gl_analytics cookie. /privacy/ states this in plain words.
// The Pinterest Tag (when a Tag ID is configured) rides the SAME choice:
// window.glLoadPinterest() exists only on builds that have one, and is only
// ever called from here or from head() when the cookie already says 1.
(function(){
  function choice(){
    var m=document.cookie.match(/(?:^|; )gl_analytics=([01])(?:;|$)/);
    return m?m[1]:null;
  }
  function set(v){
    document.cookie='gl_analytics='+v+';path=/;max-age=15552000;SameSite=Lax';
  }
  if(choice()!==null) return;
  var b=document.createElement('div');
  b.setAttribute('role','region');
  b.setAttribute('aria-label','Analytics consent');
  b.style.cssText='position:fixed;left:12px;right:12px;bottom:12px;z-index:99;'+
    'max-width:560px;margin:0 auto;background:#111418;color:#f4f1ea;'+
    'border:1px solid #2c3138;border-radius:10px;padding:12px 14px;'+
    'font:14px/1.5 system-ui,sans-serif;box-shadow:0 8px 30px rgba(0,0,0,.4)';
  b.innerHTML='<p style="margin:0 0 10px">We use Google Analytics to count page views and see which designs are popular. No advertising cookies, and we never sell data. '+
    '<a href="/privacy/" style="color:#ffb35c">Privacy policy</a>.</p>'+
    '<button type="button" data-gl="1" style="margin-right:8px;padding:8px 14px;'+
    'border:0;border-radius:8px;background:#ffb35c;color:#111418;font-weight:700;'+
    'cursor:pointer">Allow analytics</button>'+
    '<button type="button" data-gl="0" style="padding:8px 14px;border:1px solid #454b54;'+
    'border-radius:8px;background:transparent;color:#f4f1ea;cursor:pointer">No thanks</button>';
  document.addEventListener('DOMContentLoaded',function(){document.body.appendChild(b);});
  b.addEventListener('click',function(e){
    var v=e.target.getAttribute&&e.target.getAttribute('data-gl');
    if(v===null||v===undefined) return;
    set(v);
    if(b.parentNode) b.parentNode.removeChild(b);
    if(v==='1'&&window.glLoadAnalytics) window.glLoadAnalytics();
    if(v==='1'&&window.glLoadPinterest) window.glLoadPinterest();
  });
})();

// ---------- Pinterest Tag events ----------
// pintrk only exists after consent (see head()); every call is wrapped so a
// declined or unconfigured build is a silent no-op. product_id is the slug -
// the same value as `id` in /feeds/pinterest.csv - which is what lets
// Pinterest join tag events to catalogue items (dynamic retargeting, VMP).
function glPin(ev,data){try{pintrk('track',ev,data);}catch(e){}}

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
  document.querySelectorAll('a[href*="viralstyle.com"],a[href*="gridironlocker.shop"]').forEach(function(a){
    var h=a.getAttribute('href');
    if(!h||/[?&](creator|utm_source)=/.test(h))return;
    a.setAttribute('href',h+(h.indexOf('?')<0?'?':'&')+tag);
  });
})();

// ---------- SHOP NOW hand-off tracking ----------
// The only conversion action on a product page. Every button reports its
// placement (hero / apparel / footer_band / sticky_bar) so the metric that
// matters - product landing page -> partner click-through rate - is
// measurable, and so we can see WHICH CTA earns the click. The creator
// dimension (window.GL_CREATOR, set above from the persistent cookie) is
// attached to every event so attributed vs organic hand-offs split cleanly.
// The destination is read off the anchor rather than hardcoded, because
// Cleveland now hands off to the Mayzing storefront while Dallas, Green Bay
// and Michigan still hand off to Viralstyle - a fixed hostname would have
// mislabelled every migrated click.
document.querySelectorAll('a.shopnow').forEach(function(a){
  a.addEventListener('click',function(){
    var d=a.dataset||{};
    var dest=((a.getAttribute('href')||'').replace(/^https?:\/\//,'').split(/[/?]/)[0])||'unknown';
    try{gtag('event','shop_now_click',{
      item_id:d.slug,value:parseFloat(d.price||'0'),currency:'USD',
      collection:d.collection,placement:d.placement,creator:window.GL_CREATOR||'',
      destination:dest
    });}catch(e){}
    // legacy event names kept so existing GA4 reports do not break
    try{gtag('event','viralstyle_checkout_click',{
      item:d.slug,price:parseFloat(d.price||'0'),collection:d.collection,
      placement:d.placement,creator:window.GL_CREATOR||'',destination:dest
    });}catch(e){}
    try{gtag('event','viralstyle_redirect',{
      item_id:d.slug,value:parseFloat(d.price||'0'),currency:'USD',
      collection:d.collection,placement:d.placement,creator:window.GL_CREATOR||'',
      destination:dest
    });}catch(e){}
    // Pinterest 'checkout': the hand-off to the partner cart is the last
    // step this domain can observe (the transaction itself completes on
    // Mayzing/Viralstyle), so it is the checkout signal the Verified
    // Merchant Program asks for. value/currency/line_items per the spec.
    glPin('checkout',{
      value:parseFloat(d.price||'0'),order_quantity:1,currency:'USD',
      line_items:[{product_id:d.slug,product_name:document.title.split(' | ')[0],
        product_price:parseFloat(d.price||'0'),product_quantity:1,
        product_category:d.collection}]
    });
  });
});

// ---------- Pinterest category view ----------
(function(){
  var k=document.body&&document.body.getAttribute('data-collection-page');
  if(!k)return;
  glPin('viewcategory',{line_items:[{product_category:k}]});
})();

// ---------- custom-design CTA tracking ----------
// The secondary funnel (nav, footer, PDP band, collection band, contact
// page) all point at the homepage form via a.custom-link. One event with a
// placement dimension shows which entry point earns the inquiry.
document.querySelectorAll('a.custom-link').forEach(function(a){
  a.addEventListener('click',function(){
    try{gtag('event','custom_cta_click',{
      placement:(a.dataset&&a.dataset.placement)||'unknown',page:location.pathname
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
  // Pinterest 'pagevisit' with product data: the product-page event the
  // catalogue joins on (product_id == feed id).
  glPin('pagevisit',{
    currency:'USD',
    line_items:[{product_id:d.slug,product_name:document.title.split(' | ')[0],
      product_price:parseFloat(d.price||'0'),product_category:d.collection}]
  });
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

// ---------- team collection apparel buttons (.gcategory-tile) ----------
// Same garment-swap behaviour as Bella's locker, over a team page's
// #grid[data-apparel] grid of .card cards. Each click swaps, per design, the
// mockup of a garment that design actually lists, and never invents stock.
// A design with no listing for the chosen garment is REMOVED from the grid
// rather than greyed out: a category shows exactly the designs sold in it, so
// a t-shirt is never shown as a hoodie and no dead card dilutes the result.
// An entry with no image means we hold the listing but no garment render, so
// that card stays visible on its own mockup rather than vanishing.
// Clicking the active button again clears the selection and every card
// returns. Scoped to pages that emit both the tiles and the payload; without
// them this block does nothing.
(function(){
  var row=document.querySelector('.gcategory-tiles'); if(!row)return;
  var tiles=[].slice.call(row.querySelectorAll('.gcategory-tile[data-gcat]'));
  if(!tiles.length)return;
  var grid=document.querySelector('#grid[data-apparel]'); if(!grid)return;
  var matrix; try{matrix=JSON.parse(grid.getAttribute('data-apparel')||'{}');}catch(e){return;}
  var cards=[].slice.call(grid.querySelectorAll('.card[data-slug]'));
  if(!cards.length)return;
  var chips=[].slice.call(document.querySelectorAll('.gstyle-chip[data-gstyle]'));
  var chipRow=document.getElementById('gstyleRow');
  cards.forEach(function(card){
    var styles={}, byCat={}, groups=matrix[card.getAttribute('data-slug')]||{};
    Object.keys(groups).forEach(function(cat){
      var list=(groups[cat]||[]).filter(function(e){return e&&e.garment;});
      byCat[cat]=list;
      list.forEach(function(entry){
        if(!styles[entry.garment])styles[entry.garment]=entry;
      });
    });
    var img=card.querySelector('.ph img');
    // The second <img class="alt"> is the hover/back view. It is a render of
    // the design's OWN garment, so it is wrong the moment the card swaps to
    // another garment - a t-shirt back under a hoodie front.
    var back=card.querySelector('.ph img.alt');
    card._styles=styles; card._byCat=byCat; card._img=img;
    card._back=back;
    card._link=card.querySelector('a');
    card._meta=card.querySelector('.meta');
    card._name=(card.querySelector('h3')||{}).textContent||'';
    card._src=img?img.getAttribute('src'):'';
    card._alt=img?img.getAttribute('alt'):'';
    card._backSrc=back?back.getAttribute('src'):'';
    card._backAlt=back?back.getAttribute('alt'):'';
    card._ownCat=categoryOf(card.getAttribute('data-type')||'');
    card._href=card._link?card._link.getAttribute('href'):'';
    card._label=card._meta?card._meta.textContent:'';
  });
  var cat=null, garment=null, loose=false;
  var countEl=document.getElementById('count'), noresEl=document.getElementById('nores');
  function visible(card){return !card.hidden&&card.style.display!=='none';}
  // The toolbar's "N designs" line and its empty state describe what is on
  // screen. The shop filters hide with inline display and this block hides
  // with the hidden attribute, so the count has to consider both.
  var EMPTY_SEARCH='No designs match that search.',
      EMPTY_CATEGORY='No designs in this collection are listed in that category yet.';
  function refreshCount(){
    var n=cards.filter(visible).length;
    if(countEl)countEl.textContent=n+' design'+(n===1?'':'s');
    if(noresEl){
      if(!n)noresEl.textContent=cat?EMPTY_CATEGORY:EMPTY_SEARCH;
      noresEl.style.display=n?'none':'block';
    }
  }
  function press(el,on){el.setAttribute('aria-pressed',on?'true':'false');}
  // A category tile means "this garment class", so it resolves to whichever
  // style (if any) the design actually listed there. A style chip is exact:
  // a design that did not list that specific cut stays out of the swap.
  function listed(card){
    if(garment){
      if(card._styles[garment])return card._styles[garment];
      if(!loose)return null;
    }
    var list=cat?(card._byCat[cat]||[]):[];
    return list.length?list[0]:null;
  }
  // Mirrors apparel_category() in src/build.py: the card's data-type is the
  // garment the store actually sells that design in.
  function categoryOf(label){
    var s=(label||'').toLowerCase();
    if(s.indexOf('hoodie')>-1)return 'hoodies';
    if(s.indexOf('sweatshirt')>-1||s.indexOf('crewneck')>-1)return 'sweatshirts';
    if(s.indexOf('tank')>-1)return 'tank-tops';
    if(s.indexOf('crop')>-1)return 'crop-tops';
    if(s.indexOf('long sleeve')>-1||s.indexOf('long-sleeve')>-1)return 'long-sleeves';
    if(s.indexOf('beanie')>-1||s.indexOf('cap')>-1||s.indexOf('hat')>-1)return 'caps-hats';
    if(s.indexOf('tee')>-1||s.indexOf('shirt')>-1)return 't-shirts';
    return '';
  }
  // The hover <img class="alt"> is a back view of the design on the garment
  // the card was built from. That render is only correct while the card shows
  // the same garment class; the store captures a back view per design, never
  // per garment, so there is nothing to swap in for a hoodie/tank/crop. When
  // the swap changes the class the back view is switched off - hovering a
  // hoodie must never flash the t-shirt back the design was first shot on.
  function setBack(card,entry){
    if(!card._back)return;
    var shown=entry?categoryOf(entry.garment):'';
    if(shown&&shown===card._ownCat){
      if(card._backSrc)card._back.src=card._backSrc;
      if(card._backAlt)card._back.alt=card._backAlt;
      card._back.hidden=false;
      return;
    }
    card._back.hidden=true;
  }
  function restore(card){
    if(card._img){if(card._src)card._img.src=card._src; if(card._alt)card._img.alt=card._alt;}
    if(card._back){
      if(card._backSrc)card._back.src=card._backSrc;
      if(card._backAlt)card._back.alt=card._backAlt;
      card._back.hidden=false;
    }
    if(card._link&&card._href)card._link.href=card._href;
    if(card._meta&&card._label)card._meta.textContent=card._label;
    card.classList.remove('is-swapped'); card.hidden=false;
  }
  function apply(){
    cards.forEach(function(card){
      var entry=listed(card);
      if(entry){
        card.hidden=false;
        if(card._img&&entry.image){card._img.src=entry.image; card._img.alt=card._name+' design on a '+entry.garment.toLowerCase();}
        setBack(card,entry);
        if(card._link&&entry.url)card._link.href=entry.url;
        if(card._meta)card._meta.textContent=entry.garment;
        card.classList.add('is-swapped'); return;
      }
      restore(card);
      // no listing for the chosen garment: the card leaves the grid
      if(cat)card.hidden=true;
    });
    refreshCount();
    tiles.forEach(function(t){press(t,cat!==null&&t.getAttribute('data-gcat')===cat);});
    chips.forEach(function(c){press(c,garment!==null&&c.getAttribute('data-gstyle')===garment);});
    if(chipRow){ chipRow.hidden=!(cat&&chips.some(function(c){return c.getAttribute('data-gcat')===cat;})); }
  }
  function choose(nextCat,nextGarment,isTile){
    if(cat===nextCat&&(isTile||garment===nextGarment)){cat=null;garment=null;loose=false;}
    else{cat=nextCat;garment=nextGarment;loose=!!isTile;}
    apply();
    if(!cat)return;
    try{var calm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches; grid.scrollIntoView({behavior:calm?'auto':'smooth',block:'start'});}catch(e){}
  }
  // The toolbar is a separate block further down app.js, so its handlers run
  // after these and would recount the cards this block has hidden. Deferring
  // one tick puts the corrected count back on top.
  function queueCount(){setTimeout(refreshCount,0);}
  ['q','fType','fStyle','price','sort'].forEach(function(id){
    var el=document.getElementById(id); if(!el)return;
    el.addEventListener('input',queueCount); el.addEventListener('change',queueCount);
  });
  var clearBtn=document.getElementById('clearFilters');
  if(clearBtn)clearBtn.addEventListener('click',queueCount);
  tiles.forEach(function(t){t.addEventListener('click',function(){choose(t.getAttribute('data-gcat'),t.getAttribute('data-gstyle')||null,true);});});
  chips.forEach(function(c){c.addEventListener('click',function(){choose(c.getAttribute('data-gcat'),c.getAttribute('data-gstyle'),false);});});
})();

// ---------- custom design form (FormSubmit, no backend needed) ----------
// The <form> carries a real action= in the HTML, so with JavaScript disabled
// the browser posts straight to FormSubmit and the request still arrives.
// With JavaScript ON we upgrade to FormSubmit's AJAX endpoint, which returns a
// readable JSON response. The old code posted in opaque (no-cors) mode, which
// the response opaque, so .then() fired on HTTP 404/500 too and the visitor was
// told "your idea is on its way" when nothing had been delivered. Now a non-2xx
// status falls through to the mailto fallback instead of a false success, and
// the old empty setTimeout() guard (which could never fire the fallback) is
// gone.
(function(){
  var form=document.getElementById('customForm'); if(!form)return;
  var AJAX='https://formsubmit.co/ajax/'+atob(CUSTOM_EMAIL);
  var msg=document.getElementById('formmsg');
  var btn=form.querySelector('button[type=submit]');
  form.addEventListener('submit',function(e){
    // form.elements.<name> is tag-agnostic: the idea field is a textarea on
    // this version of the form and a plain input on older builds, and the
    // mailto fallback must never throw.
    var name=(form.elements.name||{}).value,
        email=(form.elements.email||{}).value,
        idea=(form.elements.idea||{}).value;
    name=name?name.trim():''; email=email?email.trim():''; idea=idea?idea.trim():'';
    if(!name||!email||!idea){msg.style.color='#c0392b';msg.textContent='Please fill in your name, email and the idea.';e.preventDefault();return;}
    e.preventDefault();
    if(btn)btn.disabled=true;
    if(msg){msg.style.color='';msg.textContent='Sending your idea...';}
    var payload={};
    new FormData(form).forEach(function(v,k){payload[k]=v;});
    function done(){
      try{gtag('event','custom_design_submit',{
        team:form.querySelector('select[name=team]').value||'',
        garment:form.querySelector('select[name=garment]').value||''
      });}catch(err){}
      if(msg){msg.style.color='';msg.textContent='Thank you '+name+'! Your idea is on its way. We will reply to '+email+' within 1-2 days.';}
      form.reset(); if(btn)btn.disabled=false;
    }
    function fallback(){
      // read() tolerates a field that is not on this version of the form -
      // the mailto fallback must never throw, it is the last resort.
      function read(sel){var el=form.querySelector(sel);return el?el.value:'';}
      var body='Name: '+name+'\nEmail: '+email+'\nTeam/theme: '+read('select[name=team]')+'\nGarment: '+read('select[name=garment]')+'\nIdea: '+idea+'\nPreferred colors: '+read('input[name=colors]')+'\nDetails: '+read('textarea[name=details]');
      window.location.href='mailto:'+atob(CUSTOM_EMAIL)+'?subject='+encodeURIComponent('Custom Design Request from '+name)+'&body='+encodeURIComponent(body);
      if(btn)btn.disabled=false;
      if(msg){msg.style.color='#c0392b';msg.textContent='We could not reach the form service. We opened your email app with the request instead - hit send and we will get back to you within 1-2 days. Or email us directly; the address is on the contact page.';}
    }
    try{
      fetch(AJAX,{method:'POST',
        headers:{'Content-Type':'application/json','Accept':'application/json'},
        body:JSON.stringify(payload)})
        .then(function(r){
          // readable response: a 4xx/5xx is a FAILURE, not a success
          if(!r.ok) throw new Error('formsubmit HTTP '+r.status);
          done();
        })
        .catch(function(){ fallback(); });
    }catch(err){ fallback(); }
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
// Same fix as the custom design form: real action= in the HTML for the no-JS
// path, AJAX endpoint with a readable status when JS is on, so a rejected
// signup can no longer be reported as "welcome to the locker".
(function(){
  var form=document.getElementById('newsForm'); if(!form)return;
  var AJAX='https://formsubmit.co/ajax/'+atob(CUSTOM_EMAIL);
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
    fetch(AJAX,{method:'POST',
      headers:{'Content-Type':'application/json','Accept':'application/json'},
      body:JSON.stringify({email:email,_subject:'New newsletter signup from gridironlocker.store'})})
      .then(function(r){
        if(!r.ok) throw new Error('formsubmit HTTP '+r.status);
        try{gtag('event','newsletter_signup',{page:location.pathname});}catch(e){}
        if(msg){msg.style.color='';msg.textContent='Welcome to the locker. Check your inbox to confirm.';}
        form.reset(); if(btn)btn.disabled=false;
      }).catch(function(){
        if(msg){msg.style.color='#c0392b';msg.textContent='We could not reach the signup service. Email us directly and we will add you by hand.';}
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
    +'<p class="muted qv-note">The design story, apparel styles, colours and sizing are on the product page. Orders are completed on the fulfilment partner.</p>'
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

// ---------- copyable promo code (.gpromobar-code) ----------
// The code stays visible in the button whether or not this runs: the click
// only copies it and flips the small "Copy" chip for a moment. A denied or
// unavailable clipboard leaves the page untouched (and the code selectable).
// .gpromobar-status is a visually hidden live region, so the confirmation is
// announced without adding visible noise to the banner.
(function(){
  var buttons=[].slice.call(document.querySelectorAll('.gpromobar-code[data-copy-code]'));
  if(!buttons.length)return;
  var status=document.querySelector('.gpromobar-status');
  function copied(btn,code,ok){
    if(!ok)return;
    var chip=btn.querySelector('.gpromobar-copy');
    if(chip&&!btn.getAttribute('data-copy-label')){
      btn.setAttribute('data-copy-label',chip.textContent);
    }
    btn.classList.add('is-copied');
    if(chip)chip.textContent='Copied';
    if(status)status.textContent='Promo code '+code+' copied.';
    if(btn._copyTimer)clearTimeout(btn._copyTimer);
    btn._copyTimer=setTimeout(function(){
      btn.classList.remove('is-copied');
      if(chip)chip.textContent=btn.getAttribute('data-copy-label')||'Copy';
    },2200);
  }
  function fallback(btn,code){
    var t=document.createElement('textarea');
    t.value=code;
    t.setAttribute('readonly','');
    t.style.position='fixed';
    t.style.left='-9999px';
    document.body.appendChild(t);
    t.select();
    var ok=false;
    try{ok=document.execCommand('copy');}catch(e){}
    document.body.removeChild(t);
    copied(btn,code,ok);
  }
  buttons.forEach(function(btn){
    btn.addEventListener('click',function(){
      var code=btn.getAttribute('data-copy-code')||'';
      if(!code)return;
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(code).then(function(){copied(btn,code,true);},
                                                 function(){fallback(btn,code);});
      }else{
        fallback(btn,code);
      }
    });
  });
})();

// ---------- creator apparel-style buttons (.gcategory-tile) ----------
// Bella's category buttons are real garment swaps over the collection grid,
// driven by the grid's data-apparel payload: per design, ONLY the garments her
// live Silent Touch store actually listed when it was captured (2026-10-12),
// each with that listing's own signed mockup and product page. One click
// therefore lands on all seven designs and never invents stock:
//   * a design that listed the chosen style swaps its mockup and both links
//     to that listing (attribution parameters included);
//   * a design that did not keeps its own mockup, muted, still linking to
//     its own product page so the visitor can check the styles that design
//     offers today;
//   * Caps & Hats is the deliberate product-list exception: its three designs
//     without a cap listing are hidden, leaving exactly the four cap cards;
//   * the five t-shirt listings get a second row of buttons, hidden until
//     one of their styles is chosen.
// There is deliberately no live status line and no per-card badge: the swap
// itself, the pressed button and each design's own product page say
// everything the shopper needs. Clicking the active style again clears the selection
// and every card returns to its own mockup. Everything is scoped to this
// page: without the tiles, or without the grid payload, the block does
// nothing at all.
(function(){
  var row=document.querySelector('.gcategory-tiles'); if(!row)return;
  var tiles=[].slice.call(row.querySelectorAll('.gcategory-tile[data-gcat]'));
  if(!tiles.length)return;
  var grid=document.querySelector('.ggrid[data-apparel]'); if(!grid)return;
  var matrix; try{matrix=JSON.parse(grid.getAttribute('data-apparel')||'{}');}catch(e){return;}
  var cards=[].slice.call(grid.querySelectorAll('.gproduct[data-slug]'));
  if(!cards.length)return;
  var chips=[].slice.call(document.querySelectorAll('.gstyle-chip[data-gstyle]'));
  var chipRow=document.getElementById('gstyleRow');
  function name(el){var s=el.querySelector('.gstyle-name')||el.querySelector('span');return s?s.textContent.trim():'';}
  cards.forEach(function(card){
    var styles={}, groups=matrix[card.getAttribute('data-slug')]||{};
    Object.keys(groups).forEach(function(cat){
      (groups[cat]||[]).forEach(function(entry){
        if(entry&&entry.garment&&!styles[entry.garment])styles[entry.garment]=entry;
      });
    });
    var img=card.querySelector('.gproduct-art img');
    var links=[].slice.call(card.querySelectorAll('a[href]'));
    var metaLabel=card.querySelector('.gproduct-meta span');
    var metaPrice=card.querySelector('.gproduct-meta b');
    card._styles=styles;
    card._img=img;
    card._links=links;
    card._metaLabel=metaLabel;
    card._metaPrice=metaPrice;
    card._name=(card.querySelector('h3')||{}).textContent||'';
    card._src=img?img.getAttribute('src'):'';
    card._alt=img?img.getAttribute('alt'):'';
    card._href=links.length?links[0].getAttribute('href'):'';
    card._garment=metaLabel?metaLabel.textContent:'';
    card._price=metaPrice?metaPrice.textContent:'';
  });
  var cat=null, garment=null;
  function press(el,on){el.setAttribute('aria-pressed',on?'true':'false');}
  function restore(card){
    if(card._img){
      if(card._src)card._img.src=card._src;
      if(card._alt)card._img.alt=card._alt;
    }
    if(card._href)card._links.forEach(function(a){a.href=card._href;});
    if(card._metaLabel)card._metaLabel.textContent=card._garment;
    if(card._metaPrice)card._metaPrice.textContent=card._price;
    card.classList.remove('is-swapped');
    card.classList.remove('is-muted');
    card.hidden=false;
  }
  function apply(){
    cards.forEach(function(card){
      var entry=garment?(card._styles[garment]||null):null;
      if(entry){
        card.hidden=false;
        if(card._img){
          card._img.src=entry.image;
          card._img.alt=card._name+' design on a '+garment.toLowerCase();
        }
        if(entry.url)card._links.forEach(function(a){a.href=entry.url;});
        if(card._metaLabel)card._metaLabel.textContent=entry.garment;
        if(card._metaPrice&&entry.price)card._metaPrice.textContent=entry.price;
        card.classList.add('is-swapped');
        card.classList.remove('is-muted');
        return;
      }
      restore(card);
      if(cat){
        if(cat==='caps-hats')card.hidden=true;
        else card.classList.add('is-muted');
      }
    });
    tiles.forEach(function(t){press(t,cat!==null&&t.getAttribute('data-gcat')===cat);});
    chips.forEach(function(c){press(c,garment!==null&&c.getAttribute('data-gstyle')===garment);});
    if(chipRow){
      chipRow.hidden=!(cat&&chips.some(function(c){
        return c.getAttribute('data-gcat')===cat;
      }));
    }
  }
  function choose(nextCat,nextGarment){
    if(cat===nextCat&&garment===nextGarment){cat=null;garment=null;}
    else{cat=nextCat;garment=nextGarment;}
    apply();
    if(!cat)return;
    try{
      var calm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      grid.scrollIntoView({behavior:calm?'auto':'smooth',block:'start'});
    }catch(e){}
  }
  tiles.forEach(function(t){
    t.addEventListener('click',function(){
      choose(t.getAttribute('data-gcat'),t.getAttribute('data-gstyle')||null);
    });
  });
  chips.forEach(function(c){
    c.addEventListener('click',function(){
      choose(c.getAttribute('data-gcat'),c.getAttribute('data-gstyle'));
    });
  });
})();
