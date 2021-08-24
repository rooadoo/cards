//// Hide different render modes ////
$card_czar    = $("#card-czar").hide();
$hand         = $('#hand').hide();

//// Websocket choose ssl if enabled on page ////
let ws_version = 'ws://';
if (location.protocol === 'https:') ws_version = 'wss://';

//// Query and store important data from page ////
// Static data embeded into page
const $gamedata = $('#gamedata');
let game_over  = $gamedata.data('gameover');
const gameid   = $gamedata.data('gameid');
const lobbyurl = $gamedata.data('data-lobbyurl');
// Jquery elements from page
$mymodalLabel = $("#mymodalLabel");
$mymodalBody = $("#mymodalBody");
$mymodal = $('#mymodal');
$blackcard = $('#blackcard-0');
$blackdeck_count = $('#blackdeck-count');
$whitedeck_count = $('#whitedeck-count');
$userlist = $('#user-list');

const chatSocket = new WebSocket(
                    ws_version
                        + window.location.host
                        + '/table/ws/game/'
                        + gameid
                        + '/'
                    );

chatSocket.onopen = function(e) {
  if (game_over === 'True') {
    notify_game_over();
    chatSocket.close();
  }
};

chatSocket.onclose = function(e) {
  console.error('ws socket closed');
};

//// enable events ////
$("#choose-winner").on('click', function () {websocket_send_action('choosewinner')});
$("#skip-round").on('click',  function () {websocket_send_action('skipround')});


function place_whitecard(add_id, add_text, replace_id, additionalclass){
  // Either create a new card and append it to hand (as is done in initial rendering) or find an existing card and
  // replace it with the new card. additionalclass will apply an additional class to the element
  const $new_card = $('<div class="card-body">').addClass(additionalclass);
  if (add_id !== null) $new_card.attr('id', 'whitecard-' + add_id);
  $new_card.append(add_text);

  if (replace_id === null){
    $hand.append(
      $('<div class="card bg-light border-dark mb-3 text-center">').append(
        $new_card));
  }
  else{
    $('#whitecard-' + replace_id).replaceWith($new_card);
  }
}

function choose_card(ev){
  let $element = $(ev.currentTarget);
  let cardid = $element.attr('id').split('-')[1];

  let action;
  if ($element.hasClass('mycard')) action = 'play_whitecard';
  else if ($element.hasClass('czarcard')) action = 'choosewinningcard';
  else{
    console.error('no known class to define card click action');
    return;
  }
  $element.parent().removeClass('border-dark').addClass('bgdisabled');
  $element.off('click');
  websocket_send_action(action, cardid);
}

function set_player_status(username, status, score, player_id){

  let $user = $("#" + player_id + '-status');

  // create user and add to DOM if does not exist
  if ($user.length === 0){
    $user  = $('<li>').attr('id', player_id + '-status');
    $user.text(' ' + username);
    $user.prepend($('<span class="badge badge-light"></span>'));

    $userlist.append($user);
  }

  // Set current values for user
  $user.find('.badge').text(score);
  $user.removeClass();
  $user.addClass('list-group-item');

  switch (status){
    case "ready":
      $user.addClass('list-group-item-success');
      break;
    case "notready":
      $user.addClass('list-group-item-warning');
      break;
    case "czar":
      $user.addClass('list-group-item-primary czar');
      break;
    case "czar_choosing":
      $user.addClass('list-group-item-warning czar');
      break;
    }
}
//// Parser for incoming websocket requests ////
chatSocket.onmessage = function(e) {
  let data = JSON.parse(e.data);
  const action = data.action;
  data = data.data;
  switch (action) {

    case 'replace_whitecard':
      place_whitecard(data.add_id, $('<p class="card-text">').text(data.add_text), data.replace_id, 'mycard');
      break;

    case "add_whitecard":
      place_whitecard(data.add_id, $('<p class="card-text">').text(data.add_text), null, 'mycard');
      break;

    case "disable_submit":
      $hand.find('.card').removeClass('border-dark').addClass('bgdisabled');
      $hand.find('.card-body').off('click');
      break;

    case "enable_submit":
      enable_submit();
      break;

    case "show_playerhand":
      show_playerhand();
      break;

    case "start_cardczar":
      $card_czar.show();
      $hand.hide();
      break;

    case "choosing_cardczar":
      $card_czar.hide();
      $hand.show();
      $hand.find(".czarcard").parent().remove();
      $hand.find(".mycard").parent().hide();
      for (let card_id in data) {
        if (!data.hasOwnProperty(card_id)) continue;
        place_whitecard(card_id, converttp(data[card_id]), null, 'czarcard');
      }
      $hand.find('.czarcard').on('click', function (ev) {choose_card(ev)});
      break;

    case "set_blackcard":
        $blackcard.empty().append($("<p class='card-text'>").text(data));
        break;

    case "player_status":
      set_player_status(data['name'], data['status'], data['score'], data['player_id']);
      break;

    case "winner_posted":
      let title = data['czar_playername'] + ' picked ' + data['winning_playername'] + "'s card";
      let $bodycontainer = $('<div>').append($('<p class="inversefont">').text($blackcard.textContent));
      $bodycontainer.append(converttp(data['card_text']));
      show_modal(title, $bodycontainer, 5);
      break;

    case "skip_notification":
      // Hup UI if you are the CZAR
      if ($("#card-czar").is(':visible')){
        show_playerhand();
        enable_submit();
      }

      show_modal(
          data['skipper'] + ' skipped ' + data['skipped'] + "'s turn as czar",
          null,
          5
        );
      break;

    case "show_candidate_cards":
        $hand.show();
        $hand.find('.mycard').parent().hide();
        $hand.find('.czarcard').parent().remove();

        data.forEach(function(cardtexts) {
          place_whitecard(null, converttp(cardtexts), null, 'czarcard');
        });
        $hand.find('.czarcard').parent().removeClass('border-dark').addClass('bgdisabled');

        break;

    case "end_game":
      game_over = 'True';
      notify_game_over();
      break;

    case "card_count":
      $blackdeck_count.text(data['black']);
      $whitedeck_count.text(data['white']);
      break;
   }
 };


//// Helper Functions ////
function converttp(listofstrings) {
  return $(listofstrings).map(function () {
    return $('<p>').text(this)
  }).get()
}

// Helper function to package websocket data into a standard form
function websocket_send_action(action, data) {
  chatSocket.send(JSON.stringify({
      'action': action,
      'data': data
  }))
}

function show_playerhand(){
  $card_czar.hide();
  $hand.show();
  $hand.find(".mycard").parent().show();
  $hand.find(".czarcard").parent().remove();
}

function enable_submit(){
  $hand.find('.card').addClass('border-dark').removeClass('bgdisabled');
  $hand.find('.card-body').on('click', function (ev) {choose_card(ev)});
}

function show_modal(title, bodyobj, timeoutseconds){

  $mymodalLabel.text(title);
  $mymodalBody.empty();

  if (bodyobj !== null) $mymodalBody.append(bodyobj);

  clearTimeout($mymodal.data('hideInterval'));

  $mymodal.data('hideInterval', setTimeout(function(){
      $mymodal.modal('hide');
      }, timeoutseconds*1000));

   $mymodal.modal('show');
}

function notify_game_over(){
  $('#skip-round').hide();
  $('#blackcard-hand').hide();
  $hand.hide();
  $card_czar.hide();

  let $alert = $("<div class='alert alert-info'><p>'Game OVER'</p></div>");
  $alert.append($('<a class="btn btn-info" role=button>').attr('href', lobbyurl).text('Click Here to Return To Lobby'));

  $('#top-pane').after($alert)
}
