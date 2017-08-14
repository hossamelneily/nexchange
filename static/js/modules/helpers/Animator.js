export default class Animator {
    static animateExchangeSign(e) {
		let el = document.getElementById('exchange-sign');
		if (!el) return;

		el.classList.remove("loading");
		void el.offsetWidth;
		el.classList.add("loading");
	}
}