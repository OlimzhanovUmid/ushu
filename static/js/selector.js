var Selector = React.createClass({displayName: "Selector",
    handleRemove : function(ev){
      console.log(this.getDOMNode());
      console.log(this.getDOMNode().parentNode);
      console.log(this.getDOMNode().parent);
      this.getDOMNode().parentNode.removeChild(this.getDOMNode());
    },
    render: function() {
        var options = this.props.values.map(function(item){
            return (React.createElement("option", {value: item['pk']}, item['name']));
        });

        res = (
        React.createElement("div", null, 
                React.createElement("select", {
                  name: this.props.select_name, 
                  className: "form-control"}, 
                    options
                ), 
                React.createElement("span", {className: "glyphicon glyphicon-remove", onClick: this.handleRemove})
        )
        );
        return res;
    },
});

function removeCombination(el) {
  console.log(el);
}

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
    var elems = items[cat_value];
    React.render(
        React.createElement(Selector, {values: elems, select_name: select_name}),
        document.getElementById(div_id)
    );
    counter.value = Number(count) + 1;
  });
});

