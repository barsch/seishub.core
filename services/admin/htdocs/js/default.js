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