(() => {
  const all = document.getElementById('select-all');
  const boxes = [...document.querySelectorAll('input[name="orders"]')];
  const update = () => {
    const count = boxes.filter(box => box.checked).length;
    document.getElementById('selection-count').textContent = `已選 ${count} 筆`;
    all.checked = boxes.length > 0 && count === boxes.length;
    all.indeterminate = count > 0 && count < boxes.length;
  };
  all.addEventListener('change', () => { boxes.forEach(box => box.checked = all.checked); update(); });
  boxes.forEach(box => box.addEventListener('change', update));
  update();
})();
