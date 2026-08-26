
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

// ---------- hero slider ----------
(function(){
  var root=document.querySelector('.hslider');
  var slides=[].slice.call(document.querySelectorAll('.hslider .slide'));
  var dots=[].slice.call(document.querySelectorAll('.hslider .hdot'));
  if(!root||!slides.length)return;
  var cur=0, timer;
  function show(i){
    cur=(i+slides.length)%slides.length;
    slides.forEach(function(s,n){
      s.classList.toggle('on',n===cur);
      s.setAttribute('aria-hidden',n===cur?'false':'true');
      // keep hidden slides out of the tab order so phone users don't
      // swipe-focus buttons they cannot see
      [].slice.call(s.querySelectorAll('a,button')).forEach(function(el){
        if(n===cur){el.removeAttribute('tabindex');}else{el.setAttribute('tabindex','-1');}
      });
    });
    dots.forEach(function(d,n){
      d.classList.toggle('on',n===cur);
      d.setAttribute('aria-current',n===cur?'true':'false');
    });
  }
  dots.forEach(function(d,n){d.addEventListener('click',function(){show(n);restart()})});
  // gentle 6.5s dwell, smooth crossfade — light, not heavy
  function restart(){clearInterval(timer);timer=setInterval(function(){show(cur+1)},6500)}
  function stop(){clearInterval(timer)}
  // swipe left/right on touch devices
  var x0=null,y0=null,locked=false;
  root.addEventListener('touchstart',function(e){
    var t=e.changedTouches[0]; x0=t.clientX; y0=t.clientY; locked=false; stop();
  },{passive:true});
  root.addEventListener('touchmove',function(e){
    if(x0===null)return;
    var t=e.changedTouches[0];
    if(!locked&&Math.abs(t.clientX-x0)>12&&Math.abs(t.clientX-x0)>Math.abs(t.clientY-y0))locked=true;
  },{passive:true});
  root.addEventListener('touchend',function(e){
    if(x0===null)return;
    var dx=e.changedTouches[0].clientX-x0;
    if(locked&&Math.abs(dx)>40)show(cur+(dx<0?1:-1));
    x0=null; restart();
  },{passive:true});
  // don't burn cycles (or battery) while the hero is off screen / tab hidden
  document.addEventListener('visibilitychange',function(){document.hidden?stop():restart()});
  if('IntersectionObserver' in window){
    new IntersectionObserver(function(en){en[0].isIntersecting?restart():stop()},{threshold:0.15}).observe(root);
  }
  show(0);
  restart();
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
      var body='Name: '+name+'\nEmail: '+email+'\nTeam/theme: '+(form.querySelector('select[name=team]').value)+'\nGarment: '+(form.querySelector('select[name=garment]').value)+'\nIdea: '+idea+'\nSizes: '+(form.querySelector('input[name=sizes]').value)+'\nDetails: '+(form.querySelector('textarea[name=details]').value);
      window.location.href='mailto:'+atob(CUSTOM_EMAIL)+'?subject='+encodeURIComponent('Custom Design Request from '+name)+'&body='+encodeURIComponent(body);
      if(msg)msg.textContent='Opening your email app with your request — hit send and we will get back to you within 1-2 days.';
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

// ---------- collection filter / search / sort ----------
(function(){
  var grid=document.getElementById('pg'); if(!grid)return;
  var cards=[].slice.call(grid.children);
  var q=document.getElementById('q'), sort=document.getElementById('sort'),
      count=document.getElementById('count'), nores=document.getElementById('nores');
  var filter='all';
  function price(c){return parseFloat(c.querySelector('.price').textContent.replace('$',''))}
  function name(c){return c.querySelector('h3').textContent.toLowerCase()}
  function type(c){return c.querySelector('.meta').textContent.trim()}
  function apply(){
    var term=(q.value||'').toLowerCase().trim(), n=0;
    cards.forEach(function(c){
      var ok=(filter==='all'||type(c)===filter)&&(!term||c.textContent.toLowerCase().indexOf(term)>-1);
      c.style.display=ok?'':'none'; if(ok){n++;c.classList.add('in');}
    });
    count.textContent=n+' design'+(n===1?'':'s');
    nores.style.display=n?'none':'block';
  }
  function resort(){
    var v=sort.value, arr=cards.slice();
    if(v==='lo')arr.sort(function(a,b){return price(a)-price(b)});
    if(v==='hi')arr.sort(function(a,b){return price(b)-price(a)});
    if(v==='az')arr.sort(function(a,b){return name(a)<name(b)?-1:1});
    arr.forEach(function(c){grid.appendChild(c)});
  }
  q&&q.addEventListener('input',apply);
  sort&&sort.addEventListener('change',resort);
  document.querySelectorAll('.chip').forEach(function(b){
    b.addEventListener('click',function(){
      document.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on')});
      b.classList.add('on'); filter=b.dataset.f; apply();
    });
  });
  var u=new URLSearchParams(location.search).get('q'); if(u&&q){q.value=u;apply();}
})();
