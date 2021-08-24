
let $office_only_btn = $("#officialonly");
let $decks = $(".deck");
let $start_btn = $("#start_btn")

function choose_deck(ev) {
    let $element = $(ev.currentTarget);
    $element.toggleClass("selecteddeck");
}

function official_click() {
    $office_only_btn.toggleClass("activated");
    if ($office_only_btn.hasClass("activated")) {
        console.debug('hiding');
        $decks.filter(":not(.official)").removeClass("selecteddeck").hide();
    }
    else {
        $decks.show();
    }
}

function start_game() {
    let ids = $('.selecteddeck').map(function () {return this.id}).get();
    $("#start_form input[name*=decks]").attr('value', ids);
    $("#start_form").submit();
}

$decks.on("click", choose_deck);
$office_only_btn.on("click", official_click);
$start_btn.on("click", start_game)
