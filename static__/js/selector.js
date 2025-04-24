var Selector = React.createClass({displayName: "Selector",
    render: function() {
        var options = this.props.items.map(function(item){
            return (React.createElement("option", {value: item['pk']}, item['name']));
        });

        res = (
                React.createElement("select", {
                  name: this.props.select_name, 
                  className: "form-control"}, 
                    options
                )
        );
        return res;
    },
});


$(document).ready(function(){
  $('span.btn').bind("click",function(){
    var cat_value = this.getAttribute('value');
    var parent = $(this).parent();
    var last_item = $(parent).find('#last_item')[0];
    var counter = $(parent).children('input[name="counter-'+ cat_value + '"]')[0];
    var count = counter.value;
    var div_id = 'div_' + cat_value + '_' + count;
    var div = '<div class="form-group" style="display: inline-block;margin-left: 10px;" id="' + div_id + '"></div>';
    $(last_item).before(div);
    var element = $(parent).children('#'+count);
    var select_name = 'cat-' + cat_value + '-' + count;
    React.render(
        React.createElement(Selector, {items: items, select_name: select_name}),
        document.getElementById(div_id)
    );
    counter.value = Number(count) + 1;
  });
});

