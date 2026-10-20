(function(){
 const normal=document.getElementById('font-normal'),large=document.getElementById('font-large');
 function apply(size){document.documentElement.dataset.textSize=size;normal?.setAttribute('aria-pressed',String(size==='normal'));large?.setAttribute('aria-pressed',String(size==='large'))}
 let saved='normal';try{saved=localStorage.getItem('lingyatong-text-size')==='large'?'large':'normal'}catch{}
 apply(saved);
 if(normal)normal.onclick=()=>{apply('normal');try{localStorage.setItem('lingyatong-text-size','normal')}catch{}};
 if(large)large.onclick=()=>{apply('large');try{localStorage.setItem('lingyatong-text-size','large')}catch{}};
})();
