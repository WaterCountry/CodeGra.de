context('HTML viewer', () => {
    let course, assig, url;

    before(() => {
        cy.visit('/');
        cy.createCourse('HTML-viewer', [
            { name: 'student1', role: 'Student' },
            { name: 'student3', role: 'Student' },
            { name: 'robin', role: 'Teacher' },
        ]).then(res => {
            course = res;
            return cy.createAssignment(course.id, 'Deadline', {
                state: 'open',
                deadline: 'tomorrow',
            });
        }).then(res => {
            assig = res;
            cy.visit(`/courses/${course.id}/assignments/${assig.id}/submissions`);
            return cy.fixture('test_submissions/html.tar.gz', 'base64').then(fileContent => {
                cy.get('.dropzone').upload(
                    {
                        fileContent,
                        fileName: 'html.tar.gz',
                        mimeType: 'text/tar',
                        encoding: 'base64',
                    },
                    { subjectType: 'drag-n-drop' },
                );
                cy.get('.submission-uploader .submit-button').submit('success', {
                    hasConfirm: true,
                    waitForState: false,
                });

                return cy.url().should('contain', '/files/').then($url => {
                    url = $url;
                });
            });
        });
    });

    function openIndex() {
        cy.visit(url);
        cy.get('.file-tree').contains('nested').click();
        cy.get('.file-tree').contains('index.html').click();
    };

    it('should open an iframe directly', () => {
        cy.login('admin', 'admin');
        openIndex();
        cy.get('.file-viewer .loader').should('not.exist');
        cy.get('.file-viewer iframe');

        cy.get('.file-viewer .alert a').click();
        cy.get('.file-viewer.code-viewer');
    });

    it('should not open an iframe directly if it is not your submission', () => {
        cy.login('robin', 'Robin');
        openIndex();

        cy.get('.file-viewer.html-viewer');
        cy.get('.file-viewer iframe').should('not.exist');

        cy.get('.file-viewer').contains('.btn', 'Show source');
        cy.get('.file-viewer').contains('.submit-button', 'Render html').submit(
            'success',
            { waitForState: false },
        );
        cy.get('.file-viewer iframe');

        cy.get('.file-viewer .alert').find('a').click();
        cy.get('.file-viewer.code-viewer');

        openIndex();
        cy.get('.file-viewer').contains('.btn', 'Show source').click();
        cy.get('.file-viewer.code-viewer');
    });
});
