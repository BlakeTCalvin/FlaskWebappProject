// For partials and username/email checking
$(".username").keyup(function(){
    let data = {username: $(this)[0].value}
    $.ajax({
        url: "/username",
        method: "POST",
        data: data
    })
    .done(function(response){
        $("#usernamemsg").html(response);
    })
})

$(".email").keyup(function(){
    let data = {email: $(this)[0].value}
    $.ajax({
        url: "/email",
        method: "POST",
        data: data
    })
    .done(function(response){
        $("#emailmsg").html(response);
    })
})

// For partials to dynamically search for users in search bar
$("#usersearch").keyup(function(){
    let data = {usersearch: $(this)[0].value}
    $.ajax({
        url: "/usersearch",
        method: "POST",
        data: data
    })
    .done(function(response){
        $("#users_container").html(response);
    })
})

// For adding active class to navbar
function activeSelector() {
    var header = document.getElementById("navbarToggle");
    var current = document.getElementsByClassName("active-nav");
    current.className = current.className.replace(" active-nav", "");
    this.className += " active-nav";
}