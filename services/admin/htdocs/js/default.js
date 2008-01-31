function toggleDisplay(element_id)
{
    var current_display = document.getElementById(element_id).style.display;
    if (current_display=='none')
    {
        document.getElementById(element_id).style.display = '';
    }
    else
    {
        document.getElementById(element_id).style.display = 'none';
    }
}

function expandAll(element_name)
{
    var elements = document.getElementsByName(element_name);
    for each (var element in elements)
    {
        var current_display = element.style.display;
        if (current_display=='none')
        {
            element.style.display = '';
        }
    }
}