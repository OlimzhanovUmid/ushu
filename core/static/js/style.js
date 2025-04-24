$(document).on('keypress', function(e) {
    var tag = e.target.tagName.toLowerCase();
    console.log(tag);
    console.log(e.which);
    if(e.which === 32){
       // user has pressed space
       $('#last-circle-item').before('<li class="circle-item"></li>');
   }
});