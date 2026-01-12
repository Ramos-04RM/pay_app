function proverka() {
    return confirm("Видалити дане поле? ");
}

function delete_item() {
    return alert(" Видалити неможливо! Даний кабінет використовуться!");
}

function my_func(i) {
     const myPsw = document.getElementById('remove-heli-' + i);
     const displaySetting = myPsw.style.display;
     const clockButton = document.getElementById('btn' + i);
     if (displaySetting === 'block') {
        myPsw.style.display = 'none';
        clockButton.innerHTML = 'Show';
    }
    else {
        myPsw.style.display = 'block';
        clockButton.innerHTML = 'Hide';
    }
}